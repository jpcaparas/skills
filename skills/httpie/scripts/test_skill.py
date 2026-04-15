#!/usr/bin/env python3
"""
test_skill.py - Validate packaging and run HTTPie probes.

Usage:
    python3 test_skill.py <skill-path>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import probe_httpie
import validate


def extract_file_references(content: str) -> list[str]:
    refs: set[str] = set()
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")

    for match in re.finditer(r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`", stripped):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.add(path)

    for match in re.finditer(r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)", stripped):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.add(path)

    return sorted(refs)


def run_tests(skill_path: str) -> dict[str, object]:
    root = Path(skill_path).resolve()
    results: dict[str, object] = {
        "skill_name": root.name,
        "tests_found": 0,
        "tags": {},
        "files_verified": {"passed": 0, "total": 0},
        "cross_references": {"passed": 0, "total": 0},
        "assertions_valid": {"passed": 0, "total": 0},
        "tag_coverage": {"passed": 0, "total": 4},
        "probe_checks": {"passed": 0, "total": 0},
        "errors": [],
        "warnings": [],
        "passed": True,
    }

    validation = validate.validate_skill(str(root))
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

            for rel_path in item.get("files", []):
                results["files_verified"]["total"] += 1
                if (root / rel_path).exists():
                    results["files_verified"]["passed"] += 1
                else:
                    results["errors"].append(f"Missing eval file reference: {rel_path}")
                    results["passed"] = False

        for tag in ["smoke", "edge", "negative", "disclosure"]:
            if tag in seen_tags:
                results["tag_coverage"]["passed"] += 1
            else:
                results["errors"].append(f"Missing eval coverage for tag: {tag}")
                results["passed"] = False

    markdown_files = [root / "SKILL.md"]
    markdown_files.extend((root / "references").rglob("*.md"))
    for md_path in markdown_files:
        content = md_path.read_text(encoding="utf-8")
        for rel_path in extract_file_references(content):
            results["cross_references"]["total"] += 1
            if (root / rel_path).exists():
                results["cross_references"]["passed"] += 1
            else:
                results["errors"].append(f"Cross-reference not found: {rel_path}")
                results["passed"] = False

    suite = probe_httpie.run_suite()
    summary = suite["summary"]
    results["probe_checks"]["total"] = summary["checks_total"]
    results["probe_checks"]["passed"] = summary["checks_passed"]
    if not suite["passed"]:
        failing = [item["name"] for item in suite["checks"] if not item["passed"]]
        results["errors"].append(f"Probe suite failed: {', '.join(failing)}")
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
        "Files verified: "
        f"{results['files_verified']['passed']}/{results['files_verified']['total']}"
    )
    print(
        "Cross-references checked: "
        f"{results['cross_references']['passed']}/{results['cross_references']['total']}"
    )
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
