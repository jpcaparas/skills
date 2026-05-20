#!/usr/bin/env python3
"""Validate packaging and run repository-readme-writer probes."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate


def run_probe_fixture(probe_script: Path) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "package.json").write_text(
            json.dumps(
                {
                    "scripts": {
                        "dev": "vite",
                        "check": "npm test",
                        "build": "vite build",
                    }
                }
            ),
            encoding="utf-8",
        )
        (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n", encoding="utf-8")
        (root / ".env.example").write_text("DATABASE_URL=\n", encoding="utf-8")
        (root / "README.md").write_text("# Fixture\n\n## Quickstart\n", encoding="utf-8")

        completed = subprocess.run(
            [sys.executable, str(probe_script), str(root)],
            check=False,
            text=True,
            capture_output=True,
        )
        if completed.returncode != 0:
            return False, completed.stderr.strip() or completed.stdout.strip()

        data = json.loads(completed.stdout)
        if data.get("package_manager") != "pnpm":
            return False, "probe did not detect pnpm from lockfile"
        if "package.json" not in data.get("manifests", []):
            return False, "probe did not report package.json"
        scripts = data.get("package_scripts", {}).get("package.json", {})
        if "dev" not in scripts or "check" not in scripts:
            return False, "probe did not report package scripts"
        if ".env.example" not in data.get("config_examples", []):
            return False, "probe did not report config example"
    return True, ""


def run_tests(skill_path: str | Path) -> dict[str, object]:
    root = Path(skill_path).resolve()
    results: dict[str, object] = {
        "skill_name": root.name,
        "tests_found": 0,
        "tags": {},
        "assertions_valid": {"passed": 0, "total": 0},
        "tag_coverage": {"passed": 0, "total": 4},
        "probe_checks": {"passed": 0, "total": 1},
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
    if not evals_path.is_file():
        results["errors"].append("evals/evals.json not found")
        results["passed"] = False
    else:
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
                if isinstance(assertion, dict) and "text" in assertion:
                    results["assertions_valid"]["passed"] += 1
                else:
                    results["errors"].append(f"Invalid assertion in eval '{eval_name}'")
                    results["passed"] = False

        for tag in ["smoke", "edge", "negative", "disclosure"]:
            if tag in seen_tags:
                results["tag_coverage"]["passed"] += 1
            else:
                results["errors"].append(f"Missing eval coverage for tag: {tag}")
                results["passed"] = False

    ok, error = run_probe_fixture(root / "scripts" / "repo_readme_probe.py")
    if ok:
        results["probe_checks"]["passed"] = 1
    else:
        results["errors"].append(f"Probe fixture failed: {error}")
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
    print(
        "Assertion format: "
        f"{results['assertions_valid']['passed']}/{results['assertions_valid']['total']} valid"
    )
    print(
        "Tag coverage: "
        f"{results['tag_coverage']['passed']}/{results['tag_coverage']['total']}"
    )
    print(
        "Probe checks: "
        f"{results['probe_checks']['passed']}/{results['probe_checks']['total']} passed"
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
