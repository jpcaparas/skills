#!/usr/bin/env python3
"""
test_skill.py - Lightweight eval and cross-reference checks for a skill.

Usage:
    python3 test_skill.py <skill-path>
"""

import json
import os
import re
import sys


def extract_file_references(content: str) -> list[str]:
    refs = []
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")
    patterns = [
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`",
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, stripped):
            path = match.group(1)
            if not placeholder_re.search(path):
                refs.append(path)
    return sorted(set(refs))


def test_skill(skill_path: str) -> dict:
    skill_path = os.path.abspath(skill_path)
    results = {
        "skill_name": os.path.basename(skill_path),
        "tests_found": 0,
        "tags": {},
        "files_verified": {"passed": 0, "total": 0},
        "cross_references": {"passed": 0, "total": 0},
        "assertions_valid": {"passed": 0, "total": 0},
        "errors": [],
        "passed": True,
    }

    evals_path = os.path.join(skill_path, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        results["errors"].append("evals/evals.json not found")
        results["passed"] = False
    else:
        with open(evals_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        evals = data.get("evals", [])
        if not isinstance(evals, list):
            results["errors"].append("'evals' field is not an array")
            results["passed"] = False
            evals = []
        results["tests_found"] = len(evals)
        for index, item in enumerate(evals):
            label = item.get("name", f"eval-{index}")
            for field in ["id", "prompt", "expected_output"]:
                if field not in item:
                    results["errors"].append(f"Eval '{label}' missing required field '{field}'")
                    results["passed"] = False
            for tag in item.get("tags", []):
                results["tags"][tag] = results["tags"].get(tag, 0) + 1
            for assertion in item.get("assertions", []):
                results["assertions_valid"]["total"] += 1
                if isinstance(assertion, dict) and "text" in assertion:
                    results["assertions_valid"]["passed"] += 1
                else:
                    results["errors"].append(f"Eval '{label}' has an invalid assertion")
                    results["passed"] = False
            for referenced_file in item.get("files", []):
                results["files_verified"]["total"] += 1
                if os.path.exists(os.path.join(skill_path, referenced_file)):
                    results["files_verified"]["passed"] += 1
                else:
                    results["errors"].append(f"Eval '{label}' references missing file: {referenced_file}")
                    results["passed"] = False

    def check_file(path: str) -> None:
        with open(path, "r", encoding="utf-8") as handle:
            for ref in extract_file_references(handle.read()):
                results["cross_references"]["total"] += 1
                if os.path.exists(os.path.join(skill_path, ref)):
                    results["cross_references"]["passed"] += 1
                else:
                    results["errors"].append(f"Cross-reference not found from {os.path.relpath(path, skill_path)}: {ref}")
                    results["passed"] = False

    skill_md = os.path.join(skill_path, "SKILL.md")
    if os.path.isfile(skill_md):
        check_file(skill_md)

    refs_dir = os.path.join(skill_path, "references")
    if os.path.isdir(refs_dir):
        for root, _, files in os.walk(refs_dir):
            for filename in files:
                if filename.endswith(".md"):
                    check_file(os.path.join(root, filename))

    return results


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        raise SystemExit(1)

    results = test_skill(sys.argv[1])
    print(f"Skill: {results['skill_name']}")
    print(f"Tests found: {results['tests_found']}")
    for tag, count in sorted(results["tags"].items()):
        print(f"  {tag}: {count}")
    print(f"Files verified: {results['files_verified']['passed']}/{results['files_verified']['total']}")
    print(f"Cross-references checked: {results['cross_references']['passed']}/{results['cross_references']['total']}")
    print(f"Assertion format: {results['assertions_valid']['passed']}/{results['assertions_valid']['total']} valid")
    if results["errors"]:
        print("\nIssues:")
        for error in results["errors"]:
            print(f"  - {error}")
    print("\nPASS: all checks passed" if results["passed"] else "\nFAIL: one or more checks failed")
    raise SystemExit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
