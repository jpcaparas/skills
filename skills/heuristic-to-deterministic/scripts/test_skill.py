#!/usr/bin/env python3
"""Validate packaging and deterministic helper behavior."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate


REQUIRED_TAGS = {"smoke", "edge", "negative", "disclosure"}


def run_classifier(script: Path) -> tuple[bool, str]:
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "README card width must be validated after install command and stop hooks should block drift",
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    if completed.returncode != 0:
        return False, completed.stderr.strip() or completed.stdout.strip()

    data = json.loads(completed.stdout)
    artifacts = {item["artifact"] for item in data.get("artifacts", [])}
    expected = {"validator", "hook-or-ci-adapter"}
    if not expected.issubset(artifacts):
        return False, f"classifier artifacts {sorted(artifacts)} did not include {sorted(expected)}"
    if data.get("primary") == "manual-review":
        return False, "classifier failed to choose a deterministic artifact"
    return True, ""


def run_tests(skill_path: str | Path) -> dict[str, object]:
    root = Path(skill_path).resolve()
    results: dict[str, object] = {
        "skill_name": root.name,
        "tests_found": 0,
        "tags": {},
        "files_verified": {"passed": 0, "total": 0},
        "assertions_valid": {"passed": 0, "total": 0},
        "tag_coverage": {"passed": 0, "total": len(REQUIRED_TAGS)},
        "helper_checks": {"passed": 0, "total": 1},
        "errors": [],
        "warnings": [],
        "passed": True,
    }

    validation = validate.validate_skill(root)
    results["warnings"].extend(validation["warnings"])
    if not validation["valid"]:
        results["errors"].extend(validation["errors"])
        results["passed"] = False

    verified_files = [
        "SKILL.md",
        "references/conversion-patterns.md",
        "references/verification.md",
        "references/gotchas.md",
        "scripts/classify_conversion.py",
        "evals/evals.json",
    ]
    results["files_verified"]["total"] = len(verified_files)
    for relative in verified_files:
        if (root / relative).is_file():
            results["files_verified"]["passed"] += 1
        else:
            results["errors"].append(f"Missing file: {relative}")
            results["passed"] = False

    evals_path = root / "evals" / "evals.json"
    if evals_path.is_file():
        evals_data = json.loads(evals_path.read_text(encoding="utf-8"))
        evals = evals_data.get("evals", [])
        results["tests_found"] = len(evals)
        seen_tags: set[str] = set()
        for item in evals:
            eval_name = item.get("name", item.get("id", "unknown"))
            for tag in item.get("tags", []):
                seen_tags.add(tag)
                results["tags"][tag] = results["tags"].get(tag, 0) + 1
            for assertion in item.get("assertions", []):
                results["assertions_valid"]["total"] += 1
                if isinstance(assertion, dict) and "text" in assertion and "type" in assertion:
                    results["assertions_valid"]["passed"] += 1
                else:
                    results["errors"].append(f"Invalid assertion in eval '{eval_name}'")
                    results["passed"] = False

        for tag in REQUIRED_TAGS:
            if tag in seen_tags:
                results["tag_coverage"]["passed"] += 1
            else:
                results["errors"].append(f"Missing eval coverage for tag: {tag}")
                results["passed"] = False

    ok, error = run_classifier(root / "scripts" / "classify_conversion.py")
    if ok:
        results["helper_checks"]["passed"] = 1
    else:
        results["errors"].append(f"Classifier fixture failed: {error}")
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
    print(
        "Assertion format: "
        f"{results['assertions_valid']['passed']}/{results['assertions_valid']['total']} valid"
    )
    print(
        "Tag coverage: "
        f"{results['tag_coverage']['passed']}/{results['tag_coverage']['total']}"
    )
    print(
        "Helper checks: "
        f"{results['helper_checks']['passed']}/{results['helper_checks']['total']} passed"
    )

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
