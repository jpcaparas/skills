#!/usr/bin/env python3
"""
test_skill.py — Validate packaging and run deterministic probes for seo-analysis.

Usage:
    python3 test_skill.py <skill-path>
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import build_fix_prompt
import probe_seo_analysis


def extract_file_references(content: str) -> list[str]:
    refs = []
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")

    for match in re.finditer(r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`", stripped):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.append(path)

    for match in re.finditer(r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)", stripped):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.append(path)

    return sorted(set(refs))


def run_tests(skill_path: str) -> dict:
    skill_path = os.path.abspath(skill_path)
    results = {
        "skill_name": os.path.basename(skill_path),
        "tests_found": 0,
        "tags": {},
        "files_verified": {"passed": 0, "total": 0},
        "cross_references": {"passed": 0, "total": 0},
        "assertions_valid": {"passed": 0, "total": 0},
        "probe_checks": {"passed": 0, "total": 0},
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
                if isinstance(assertion, dict) and "text" in assertion:
                    results["assertions_valid"]["passed"] += 1
                else:
                    results["errors"].append(f"Invalid assertion in eval '{item.get('name', item.get('id'))}'")
                    results["passed"] = False
            for file_ref in item.get("files", []):
                results["files_verified"]["total"] += 1
                if os.path.exists(os.path.join(skill_path, file_ref)):
                    results["files_verified"]["passed"] += 1
                else:
                    results["errors"].append(f"Missing eval file reference: {file_ref}")
                    results["passed"] = False

    markdown_files = [os.path.join(skill_path, "SKILL.md")]
    refs_dir = os.path.join(skill_path, "references")
    for root, _dirs, files in os.walk(refs_dir):
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

    normalized = build_fix_prompt.normalize_findings(
        [
            {"severity": "medium", "category": "metadata", "scope": "home", "evidence": "same title", "fix_direction": "route-aware title"},
            {"severity": "blocker", "category": "crawlability", "scope": "docs", "evidence": "noindex", "fix_direction": "remove accidental noindex"},
        ]
    )
    probe_expectations = [
        ("normalize-order", normalized[0]["severity"] == "blocker"),
        ("normalize-count", len(normalized) == 2),
    ]

    for name, passed in probe_expectations:
        results["probe_checks"]["total"] += 1
        if passed:
            results["probe_checks"]["passed"] += 1
        else:
            results["errors"].append(f"Probe expectation failed: {name}")
            results["passed"] = False

    suite = probe_seo_analysis.run_suite()
    results["probe_checks"]["total"] += suite["summary"]["checks_total"]
    results["probe_checks"]["passed"] += suite["summary"]["checks_passed"]
    if not suite["passed"]:
        results["errors"].append("Deterministic probe suite failed")
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
    print(f"Cross-references checked: {results['cross_references']['passed']}/{results['cross_references']['total']}")
    print(f"Assertion format: {results['assertions_valid']['passed']}/{results['assertions_valid']['total']} valid")
    print(f"Probe checks: {results['probe_checks']['passed']}/{results['probe_checks']['total']} passed")

    if results["errors"]:
        print("\nIssues:")
        for issue in results["errors"]:
            print(f"  - {issue}")

    print("\nPASS: all checks passed" if results["passed"] else "\nFAIL: one or more checks failed")
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
