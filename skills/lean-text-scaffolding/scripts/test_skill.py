#!/usr/bin/env python3
"""Run lightweight validation and local audit checks for lean-text-scaffolding."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate


BLOATED_TSX = """
export function Page() {
  return (
    <main>
      <span>Features</span>
      <h1>Everything you need to unlock your seamless workflows</h1>
      <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
      <article>
        <h2>Feature one</h2>
        <p>Short description</p>
      </article>
      <input placeholder="Email" />
    </main>
  )
}
"""

LEAN_TSX = """
export function Page() {
  return (
    <main>
      <h1>Track renewals before dates slip</h1>
      <p>See contract owners, renewal windows, and stale follow-up in one view.</p>
      <label htmlFor="email">Email</label>
      <input id="email" type="email" />
      <button>Create report</button>
    </main>
  )
}
"""


def run_bun_audit(root: Path) -> tuple[list[str], list[str], dict[str, int]]:
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"audit_checks": 0, "audit_passed": 0}
    bun = shutil.which("bun")
    if not bun:
        warnings.append("bun not found; skipped scripts/audit_lean_text.ts execution")
        return errors, warnings, metrics

    script = root / "scripts" / "audit_lean_text.ts"
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        bloated = tmpdir / "bloated.tsx"
        lean = tmpdir / "lean.tsx"
        bloated.write_text(BLOATED_TSX, encoding="utf-8")
        lean.write_text(LEAN_TSX, encoding="utf-8")

        lean_run = subprocess.run(
            [bun, str(script), "--json", str(lean)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        metrics["audit_checks"] += 1
        if lean_run.returncode == 0:
            metrics["audit_passed"] += 1
        else:
            errors.append("Lean fixture failed audit: " + (lean_run.stderr or lean_run.stdout).strip())

        bloated_run = subprocess.run(
            [bun, str(script), "--json", str(bloated)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        metrics["audit_checks"] += 1
        if bloated_run.returncode == 0:
            errors.append("Bloated fixture unexpectedly passed audit")
        else:
            try:
                payload = json.loads(bloated_run.stdout)
                rules = {
                    issue["rule"]
                    for report in payload.get("reports", [])
                    for issue in report.get("issues", [])
                }
                expected = {"placeholder-lorem", "placeholder-token", "placeholder-only-input"}
                missing = expected - rules
                if missing:
                    errors.append("Bloated fixture missed rules: " + ", ".join(sorted(missing)))
                else:
                    metrics["audit_passed"] += 1
            except json.JSONDecodeError as exc:
                errors.append(f"Bloated fixture did not emit valid JSON: {exc}")

    return errors, warnings, metrics


def run_tests(skill_path: str | Path) -> dict[str, object]:
    root = Path(skill_path).resolve()
    results: dict[str, object] = {
        "skill_name": root.name,
        "tests_found": 0,
        "tags": {},
        "files_verified": {"passed": 0, "total": 0},
        "assertions_valid": {"passed": 0, "total": 0},
        "tag_coverage": {"passed": 0, "total": 4},
        "audit": {"passed": 0, "total": 0},
        "errors": [],
        "warnings": [],
        "passed": True,
    }

    validation = validate.validate_skill(root)
    results["warnings"].extend(validation["warnings"])
    if not validation["valid"]:
        results["errors"].extend(validation["errors"])
        results["passed"] = False

    evals_path = root / "evals" / "evals.json"
    evals_data = json.loads(evals_path.read_text(encoding="utf-8"))
    evals = evals_data.get("evals", [])
    results["tests_found"] = len(evals)
    seen_tags: set[str] = set()

    for item in evals:
        eval_name = item.get("name", item.get("id", "unknown"))
        for tag in item.get("tags", []):
            seen_tags.add(tag)
            results["tags"][tag] = int(results["tags"].get(tag, 0)) + 1
        for assertion in item.get("assertions", []):
            results["assertions_valid"]["total"] += 1
            if isinstance(assertion, dict) and assertion.get("text") and assertion.get("type"):
                results["assertions_valid"]["passed"] += 1
            else:
                results["errors"].append(f"Invalid assertion in eval '{eval_name}'")
                results["passed"] = False
        for rel_path in item.get("files", []):
            results["files_verified"]["total"] += 1
            if (root / rel_path).exists():
                results["files_verified"]["passed"] += 1
            else:
                results["errors"].append(f"Missing eval file reference: {rel_path}")
                results["passed"] = False

    for tag in validate.REQUIRED_EVAL_TAGS:
        if tag in seen_tags:
            results["tag_coverage"]["passed"] += 1
        else:
            results["errors"].append(f"Missing eval coverage for tag: {tag}")
            results["passed"] = False

    audit_errors, audit_warnings, audit_metrics = run_bun_audit(root)
    results["warnings"].extend(audit_warnings)
    results["errors"].extend(audit_errors)
    results["audit"]["total"] = audit_metrics["audit_checks"]
    results["audit"]["passed"] = audit_metrics["audit_passed"]
    if audit_errors:
        results["passed"] = False

    return results


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1

    results = run_tests(sys.argv[1])
    print(f"Skill: {results['skill_name']}")
    print(f"Tests found: {results['tests_found']}")
    for tag, count in sorted(results["tags"].items()):
        print(f"  {tag}: {count}")
    print(f"Files verified: {results['files_verified']['passed']}/{results['files_verified']['total']}")
    print(f"Assertion format: {results['assertions_valid']['passed']}/{results['assertions_valid']['total']} valid")
    print(f"Tag coverage: {results['tag_coverage']['passed']}/{results['tag_coverage']['total']}")
    print(f"Audit checks: {results['audit']['passed']}/{results['audit']['total']} passed")

    if results["warnings"]:
        print("\nWarnings:")
        for warning in results["warnings"]:
            print(f"  - {warning}")
    if results["errors"]:
        print("\nIssues:")
        for issue in results["errors"]:
            print(f"  - {issue}")

    print("\nPASS: all checks passed" if results["passed"] else "\nFAIL: one or more checks failed")
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
