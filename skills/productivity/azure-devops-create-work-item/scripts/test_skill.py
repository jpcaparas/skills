#!/usr/bin/env python3
"""
test_skill.py — Lightweight skill testing (validation, not execution).

Usage:
    python3 test_skill.py <skill-path>
"""

from __future__ import annotations

import json
import os
import re
import sys


def extract_file_references(content: str) -> list[str]:
    refs = []
    stripped = re.sub(r'```[\s\S]*?```', "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")

    for match in re.finditer(r'`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`', stripped):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.append(path)

    for match in re.finditer(r'\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)', stripped):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.append(path)

    return list(set(refs))


def test_skill(skill_path: str) -> dict:
    skill_path = os.path.abspath(skill_path)
    skill_name = os.path.basename(skill_path)

    results = {
        "skill_name": skill_name,
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
        try:
            with open(evals_path, "r", encoding="utf-8") as handle:
                evals_data = json.load(handle)
        except json.JSONDecodeError as exc:
            results["errors"].append(f"evals/evals.json is not valid JSON: {exc}")
            results["passed"] = False
            evals_data = None

        if evals_data is not None:
            evals_list = evals_data.get("evals", [])
            if not isinstance(evals_list, list):
                results["errors"].append("'evals' field is not an array")
                results["passed"] = False
                evals_list = []

            results["tests_found"] = len(evals_list)

            for index, evaluation in enumerate(evals_list):
                eval_label = evaluation.get("name", f"eval-{index}")

                for field in ["id", "prompt", "expected_output"]:
                    if field not in evaluation:
                        results["errors"].append(
                            f"Eval '{eval_label}': missing required field '{field}'"
                        )
                        results["passed"] = False

                tags = evaluation.get("tags", [])
                for tag in tags:
                    results["tags"][tag] = results["tags"].get(tag, 0) + 1

                assertions = evaluation.get("assertions", [])
                for assertion_index, assertion in enumerate(assertions):
                    results["assertions_valid"]["total"] += 1
                    if not isinstance(assertion, dict):
                        results["errors"].append(
                            f"Eval '{eval_label}': assertion {assertion_index} is not an object"
                        )
                        results["passed"] = False
                        continue

                    if "text" not in assertion:
                        results["errors"].append(
                            f"Eval '{eval_label}': assertion {assertion_index} missing 'text' field"
                        )
                        results["passed"] = False
                    else:
                        results["assertions_valid"]["passed"] += 1

                    valid_types = {"functional", "structural", "disclosure", "negative", "verification"}
                    assertion_type = assertion.get("type", "")
                    if assertion_type and assertion_type not in valid_types:
                        results["errors"].append(
                            f"Eval '{eval_label}': assertion {assertion_index} has unknown type "
                            f"'{assertion_type}' (expected: {', '.join(sorted(valid_types))})"
                        )

                files = evaluation.get("files", [])
                for file_path in files:
                    results["files_verified"]["total"] += 1
                    full_path = os.path.join(skill_path, file_path)
                    if os.path.exists(full_path):
                        results["files_verified"]["passed"] += 1
                    else:
                        results["errors"].append(
                            f"Eval '{eval_label}': referenced file not found: {file_path}"
                        )
                        results["passed"] = False

    skill_md_path = os.path.join(skill_path, "SKILL.md")
    if os.path.isfile(skill_md_path):
        with open(skill_md_path, "r", encoding="utf-8") as handle:
            content = handle.read()

        refs = extract_file_references(content)
        for ref in refs:
            results["cross_references"]["total"] += 1
            ref_path = os.path.join(skill_path, ref)
            if os.path.exists(ref_path):
                results["cross_references"]["passed"] += 1
            else:
                results["errors"].append(f"Cross-reference not found: {ref}")
                results["passed"] = False

    refs_dir = os.path.join(skill_path, "references")
    if os.path.isdir(refs_dir):
        for root, _, files in os.walk(refs_dir):
            for fname in files:
                if fname == ".gitkeep" or not fname.endswith(".md"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as handle:
                        ref_content = handle.read()
                    ref_refs = extract_file_references(ref_content)
                    for ref in ref_refs:
                        results["cross_references"]["total"] += 1
                        ref_path = os.path.join(skill_path, ref)
                        if os.path.exists(ref_path):
                            results["cross_references"]["passed"] += 1
                        else:
                            results["errors"].append(
                                f"Cross-reference in {os.path.relpath(fpath, skill_path)} "
                                f"not found: {ref}"
                            )
                            results["passed"] = False
                except (OSError, UnicodeDecodeError):
                    pass

    return results


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        sys.exit(1)

    skill_path = sys.argv[1]
    if not os.path.isdir(skill_path):
        print(f"Error: '{skill_path}' is not a directory", file=sys.stderr)
        sys.exit(1)

    results = test_skill(skill_path)

    print(f"Skill: {results['skill_name']}")
    print(f"Tests found: {results['tests_found']}")

    if results["tags"]:
        for tag, count in sorted(results["tags"].items()):
            print(f"  {tag}: {count}")

    files_verified = results["files_verified"]
    print(f"Files verified: {files_verified['passed']}/{files_verified['total']}")

    cross_references = results["cross_references"]
    print(f"Cross-references checked: {cross_references['passed']}/{cross_references['total']}")

    assertions_valid = results["assertions_valid"]
    print(f"Assertion format: {assertions_valid['passed']}/{assertions_valid['total']} valid")

    if results["errors"]:
        print(f"\nIssues ({len(results['errors'])}):")
        for error in results["errors"]:
            print(f"  - {error}")

    print()
    if results["passed"]:
        print("PASS: all checks passed")
    else:
        print("FAIL: one or more checks failed")

    sys.exit(0 if results["passed"] else 1)


if __name__ == "__main__":
    main()
