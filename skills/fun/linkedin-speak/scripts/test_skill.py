#!/usr/bin/env python3
"""
test_skill.py - Lightweight checks for linkedin-speak.
"""

from __future__ import annotations

import json
import os
import py_compile
import re
import subprocess
import sys
from pathlib import Path


EXPECTED_PHRASES = [
    "deterministic local translator",
    "Kagi comparison link",
]
PYTHON_SCRIPTS = [
    "scripts/linkedin_speak.py",
    "scripts/probe_linkedin_speak.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
]


def extract_file_references(content: str) -> list[str]:
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")
    refs: set[str] = set()
    for pattern in [
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`",
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
    ]:
        for match in re.finditer(pattern, stripped):
            path = match.group(1)
            if not placeholder_re.search(path):
                refs.add(path)
    return sorted(refs)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def test_skill(skill_path: Path) -> dict:
    results = {
        "skill_name": skill_path.name,
        "tests_found": 0,
        "files_verified": {"passed": 0, "total": 0},
        "cross_references": {"passed": 0, "total": 0},
        "syntax_checks": {"passed": 0, "total": 0},
        "behavior_checks": {"passed": 0, "total": 0},
        "errors": [],
        "passed": True,
    }

    evals = load_json(skill_path / "evals" / "evals.json")
    eval_items = evals.get("evals", [])
    results["tests_found"] = len(eval_items)
    for eval_item in eval_items:
        for rel_path in eval_item.get("files", []):
            results["files_verified"]["total"] += 1
            if (skill_path / rel_path).exists():
                results["files_verified"]["passed"] += 1
            else:
                results["errors"].append(f"Eval referenced file not found: {rel_path}")
                results["passed"] = False

    skill_md = (skill_path / "SKILL.md").read_text(encoding="utf-8")
    for phrase in EXPECTED_PHRASES:
        if phrase not in skill_md:
            results["errors"].append(f"SKILL.md is missing required phrase: {phrase!r}")
            results["passed"] = False

    for ref in extract_file_references(skill_md):
        results["cross_references"]["total"] += 1
        if (skill_path / ref).exists():
            results["cross_references"]["passed"] += 1
        else:
            results["errors"].append(f"Cross-reference not found: {ref}")
            results["passed"] = False

    for ref_file in (skill_path / "references").glob("*.md"):
        content = ref_file.read_text(encoding="utf-8")
        for ref in extract_file_references(content):
            results["cross_references"]["total"] += 1
            if (skill_path / ref).exists():
                results["cross_references"]["passed"] += 1
            else:
                results["errors"].append(f"Cross-reference in {ref_file.name} not found: {ref}")
                results["passed"] = False

    for rel_path in PYTHON_SCRIPTS:
        results["syntax_checks"]["total"] += 1
        try:
            py_compile.compile(str(skill_path / rel_path), doraise=True)
            results["syntax_checks"]["passed"] += 1
        except py_compile.PyCompileError as exc:
            results["errors"].append(f"Python compile failed for {rel_path}: {exc.msg}")
            results["passed"] = False

    results["behavior_checks"]["total"] += 1
    probe = run(["python3", str(skill_path / "scripts" / "probe_linkedin_speak.py")])
    if probe.returncode == 0:
        results["behavior_checks"]["passed"] += 1
    else:
        results["errors"].append(f"Probe failed: {probe.stdout.strip()} {probe.stderr.strip()}".strip())
        results["passed"] = False

    return results


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1

    skill_path = Path(sys.argv[1]).resolve()
    results = test_skill(skill_path)

    print(f"Skill: {results['skill_name']}")
    print(f"Tests found: {results['tests_found']}")
    print(f"Files verified: {results['files_verified']['passed']}/{results['files_verified']['total']}")
    print(f"Cross-references checked: {results['cross_references']['passed']}/{results['cross_references']['total']}")
    print(f"Syntax checks: {results['syntax_checks']['passed']}/{results['syntax_checks']['total']}")
    print(f"Behavior checks: {results['behavior_checks']['passed']}/{results['behavior_checks']['total']}")
    if results["errors"]:
        print("\nIssues:")
        for error in results["errors"]:
            print(f"  - {error}")
    print("\nPASS: all checks passed" if results["passed"] else "\nFAIL: one or more checks failed")
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
