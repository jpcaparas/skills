#!/usr/bin/env python3
"""Run lightweight packaging and content tests for product-question."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


REQUIRED_TAGS = {"smoke", "edge", "negative", "disclosure"}


def extract_file_references(content: str) -> list[str]:
    refs: list[str] = []
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|\s")
    patterns = [
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`",
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
    ]
    for pattern in patterns:
        for path in re.findall(pattern, stripped):
            if not placeholder_re.search(path):
                refs.append(path)
    return sorted(set(refs))


def run_tests(skill_path: str) -> dict:
    skill_path = os.path.abspath(skill_path)
    results = {
        "skill_name": os.path.basename(skill_path),
        "tests_found": 0,
        "tags": {},
        "cross_references": {"passed": 0, "total": 0},
        "assertions_valid": {"passed": 0, "total": 0},
        "content_checks": {"passed": 0, "total": 0},
        "errors": [],
        "passed": True,
    }

    evals_path = os.path.join(skill_path, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        results["errors"].append("evals/evals.json not found")
        results["passed"] = False
    else:
        evals_data = json.loads(Path(evals_path).read_text(encoding="utf-8"))
        evals_list = evals_data.get("evals", [])
        results["tests_found"] = len(evals_list)
        for item in evals_list:
            for tag in item.get("tags", []):
                results["tags"][tag] = results["tags"].get(tag, 0) + 1
            for assertion in item.get("assertions", []):
                results["assertions_valid"]["total"] += 1
                if isinstance(assertion, dict) and "text" in assertion and "type" in assertion:
                    results["assertions_valid"]["passed"] += 1
                else:
                    results["errors"].append(f"Invalid assertion in eval '{item.get('name', item.get('id'))}'")
                    results["passed"] = False

    missing_tags = sorted(REQUIRED_TAGS - set(results["tags"]))
    if missing_tags:
        results["errors"].append("Missing eval tags: " + ", ".join(missing_tags))
        results["passed"] = False

    markdown_files = [
        os.path.join(skill_path, "SKILL.md"),
        os.path.join(skill_path, "README.md"),
        os.path.join(skill_path, "AGENTS.md"),
    ]
    for root, _dirs, files in os.walk(os.path.join(skill_path, "references")):
        for fname in files:
            if fname.endswith(".md"):
                markdown_files.append(os.path.join(root, fname))

    for markdown_path in markdown_files:
        refs = extract_file_references(Path(markdown_path).read_text(encoding="utf-8"))
        for ref in refs:
            results["cross_references"]["total"] += 1
            if os.path.exists(os.path.join(skill_path, ref)):
                results["cross_references"]["passed"] += 1
            else:
                results["errors"].append(f"Cross-reference not found: {ref}")
                results["passed"] = False

    skill_content = Path(os.path.join(skill_path, "SKILL.md")).read_text(encoding="utf-8")
    answer_contract = Path(os.path.join(skill_path, "references", "answer-contract.md")).read_text(encoding="utf-8")
    discovery = Path(os.path.join(skill_path, "references", "discovery.md")).read_text(encoding="utf-8")
    template = Path(os.path.join(skill_path, "templates", "product-answer.md")).read_text(encoding="utf-8")

    checks = [
        ("decision-tree", "## Decision Tree" in skill_content),
        ("quick-reference", "## Quick Reference" in skill_content),
        ("share-ready-standard", "## Share-Ready Answer Standard" in skill_content),
        ("no-code-default", "no code" in skill_content.lower() or "code blocks" in skill_content.lower()),
        ("answer-short-answer", "Short answer" in answer_contract),
        ("answer-checked-line", "Checked:" in answer_contract),
        ("discovery-confidence", "Confidence Labels" in discovery),
        ("template-confidence", "Confidence:" in template),
    ]

    for name, passed in checks:
        results["content_checks"]["total"] += 1
        if passed:
            results["content_checks"]["passed"] += 1
        else:
            results["errors"].append(f"Content check failed: {name}")
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
    print(f"Cross-references checked: {results['cross_references']['passed']}/{results['cross_references']['total']}")
    print(f"Assertion format: {results['assertions_valid']['passed']}/{results['assertions_valid']['total']} valid")
    print(f"Content checks: {results['content_checks']['passed']}/{results['content_checks']['total']} passed")

    if results["errors"]:
        print("\nIssues:")
        for issue in results["errors"]:
            print(f"  - {issue}")

    print("\nPASS: all checks passed" if results["passed"] else "\nFAIL: one or more checks failed")
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
