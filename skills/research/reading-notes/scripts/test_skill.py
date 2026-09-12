#!/usr/bin/env python3
"""Run packaging and helper tests for reading-notes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import probe_reading_notes
import validate


REQUIRED_TAGS = {"smoke", "edge", "negative", "disclosure"}


def check_evals(root: Path, results: dict[str, Any]) -> None:
    evals_path = root / "evals" / "evals.json"
    try:
        data = json.loads(evals_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        results["errors"].append(f"cannot read evals/evals.json: {exc}")
        results["passed"] = False
        return

    evals = data.get("evals", [])
    results["tests_found"] = len(evals)
    seen_tags: set[str] = set()

    for index, item in enumerate(evals):
        label = item.get("name", f"eval-{index}")
        for field in ["id", "name", "prompt", "expected_output"]:
            if field not in item:
                results["errors"].append(f"eval '{label}' missing required field: {field}")
                results["passed"] = False

        for tag in item.get("tags", []):
            seen_tags.add(tag)
            results["tags"][tag] = results["tags"].get(tag, 0) + 1

        for assertion in item.get("assertions", []):
            results["assertions_valid"]["total"] += 1
            if isinstance(assertion, dict) and assertion.get("text"):
                results["assertions_valid"]["passed"] += 1
            else:
                results["errors"].append(f"eval '{label}' has invalid assertion")
                results["passed"] = False

        for rel_path in item.get("files", []):
            results["files_verified"]["total"] += 1
            if (root / rel_path).exists():
                results["files_verified"]["passed"] += 1
            else:
                results["errors"].append(f"eval '{label}' references missing file: {rel_path}")
                results["passed"] = False

    for tag in sorted(REQUIRED_TAGS):
        if tag in seen_tags:
            results["tag_coverage"]["passed"] += 1
        else:
            results["errors"].append(f"missing eval coverage for tag: {tag}")
            results["passed"] = False
    results["tag_coverage"]["total"] = len(REQUIRED_TAGS)


def run_subprocess(label: str, command: list[str], results: dict[str, Any]) -> None:
    completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    results["commands"].append({"label": label, "returncode": completed.returncode})
    if completed.returncode != 0:
        output = (completed.stdout + completed.stderr).strip()
        results["errors"].append(f"{label} failed: {output}")
        results["passed"] = False


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1

    root = Path(sys.argv[1]).resolve()
    results: dict[str, Any] = {
        "skill": root.name,
        "passed": True,
        "tests_found": 0,
        "tags": {},
        "files_verified": {"passed": 0, "total": 0},
        "assertions_valid": {"passed": 0, "total": 0},
        "tag_coverage": {"passed": 0, "total": 0},
        "probe_checks": {"passed": 0, "total": 0},
        "commands": [],
        "errors": [],
        "warnings": [],
    }

    validation = validate.validate_skill(root)
    results["warnings"].extend(validation["warnings"])
    if not validation["valid"]:
        results["errors"].extend(validation["errors"])
        results["passed"] = False

    check_evals(root, results)

    suite = probe_reading_notes.run_suite()
    summary = suite["summary"]
    results["probe_checks"]["passed"] = summary["checks_passed"]
    results["probe_checks"]["total"] = summary["checks_total"]
    if not suite["passed"]:
        failing = [check["source"] for check in suite["checks"] if not check["passed"]]
        results["errors"].append("probe classifier failed for: " + ", ".join(failing))
        results["passed"] = False

    run_subprocess(
        "probe help",
        [sys.executable, str(root / "scripts" / "probe_reading_notes.py"), "--help"],
        results,
    )
    run_subprocess(
        "probe self-test",
        [sys.executable, str(root / "scripts" / "probe_reading_notes.py"), "--self-test"],
        results,
    )

    print(json.dumps(results, indent=2))
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
