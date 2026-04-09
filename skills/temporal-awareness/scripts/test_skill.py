#!/usr/bin/env python3
"""
test_skill.py — Validate packaging and run deterministic probes for temporal-awareness.

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

import capture_temporal_context
import probe_temporal_awareness
import recency_guard


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
        with open(evals_path, "r", encoding="utf-8") as handle:
            evals_data = json.load(handle)
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

    for markdown_path in [os.path.join(skill_path, "SKILL.md")]:
        with open(markdown_path, "r", encoding="utf-8") as handle:
            refs = extract_file_references(handle.read())
        for ref in refs:
            results["cross_references"]["total"] += 1
            if os.path.exists(os.path.join(skill_path, ref)):
                results["cross_references"]["passed"] += 1
            else:
                results["errors"].append(f"Cross-reference not found: {ref}")
                results["passed"] = False

    refs_dir = os.path.join(skill_path, "references")
    for root, _dirs, files in os.walk(refs_dir):
        for fname in files:
            if not fname.endswith(".md"):
                continue
            with open(os.path.join(root, fname), "r", encoding="utf-8") as handle:
                refs = extract_file_references(handle.read())
            for ref in refs:
                results["cross_references"]["total"] += 1
                if os.path.exists(os.path.join(skill_path, ref)):
                    results["cross_references"]["passed"] += 1
                else:
                    results["errors"].append(f"Cross-reference not found: {ref}")
                    results["passed"] = False

    context = capture_temporal_context.capture_context(["America/New_York"])
    probe_expectations = [
        ("context-local", bool(context["local"]["iso"])),
        ("context-timezone", bool(context["timezone"]["primary"])),
        (
            "guard-latest-model",
            recency_guard.analyze_prompt("What is the latest OpenAI model for coding?")["requires_live_verification"],
        ),
        (
            "guard-timeless",
            not recency_guard.analyze_prompt("Explain the TCP three-way handshake.")["requires_temporal_anchor"],
        ),
    ]

    for name, passed in probe_expectations:
        results["probe_checks"]["total"] += 1
        if passed:
            results["probe_checks"]["passed"] += 1
        else:
            results["errors"].append(f"Probe expectation failed: {name}")
            results["passed"] = False

    suite = probe_temporal_awareness.run_suite()
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
        "Probe checks: "
        f"{results['probe_checks']['passed']}/{results['probe_checks']['total']} passed"
    )

    if results["errors"]:
        print("\nIssues:")
        for issue in results["errors"]:
            print(f"  - {issue}")

    print("\nPASS: all checks passed" if results["passed"] else "\nFAIL: one or more checks failed")
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
