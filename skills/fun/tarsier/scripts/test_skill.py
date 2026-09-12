#!/usr/bin/env python3
"""
test_skill.py - Lightweight behavioral checks for the tarsier skill.

Usage:
    python3 test_skill.py <skill-path>

Exit codes:
    0 = all checks passed
    1 = one or more checks failed
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from pathlib import Path


REQUIRED_EXECUTABLES = [
    "scripts/rasterize.py",
]
STATIC_PROMPT = "Generate an SVG of a tarsier riding a bicycle"


def extract_file_references(content: str) -> list[str]:
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")
    refs: set[str] = set()

    for match in re.finditer(
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`", stripped
    ):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.add(path)

    for match in re.finditer(
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
        stripped,
    ):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.add(path)

    return sorted(refs)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_skill(skill_path: Path) -> dict:
    results: dict[str, object] = {
        "skill_name": skill_path.name,
        "tests_found": 0,
        "tag_counts": Counter(),
        "files_verified": {"passed": 0, "total": 0},
        "cross_references": {"passed": 0, "total": 0},
        "assertions": {"valid": 0, "total": 0},
        "errors": [],
        "passed": True,
    }

    evals_path = skill_path / "evals" / "evals.json"
    if not evals_path.is_file():
        results["errors"].append("evals/evals.json not found")
        results["passed"] = False
    else:
        evals_data = load_json(evals_path)
        evals_list = evals_data.get("evals", [])
        results["tests_found"] = len(evals_list)

        for eval_item in evals_list:
            for tag in eval_item.get("tags", []):
                results["tag_counts"][tag] += 1

            for rel_path in eval_item.get("files", []):
                results["files_verified"]["total"] += 1
                if (skill_path / rel_path).exists():
                    results["files_verified"]["passed"] += 1
                else:
                    results["errors"].append(
                        f"Eval referenced file not found: {rel_path}"
                    )
                    results["passed"] = False

            for assertion in eval_item.get("assertions", []):
                results["assertions"]["total"] += 1
                if isinstance(assertion, dict) and assertion.get("text") and assertion.get("type"):
                    results["assertions"]["valid"] += 1
                else:
                    results["errors"].append(
                        f"Eval '{eval_item.get('name', '?')}' has an assertion "
                        "missing text or type"
                    )
                    results["passed"] = False

    skill_md_path = skill_path / "SKILL.md"
    if not skill_md_path.is_file():
        results["errors"].append("SKILL.md not found")
        results["passed"] = False
        return results

    skill_md = skill_md_path.read_text(encoding="utf-8")

    for ref in extract_file_references(skill_md):
        results["cross_references"]["total"] += 1
        if (skill_path / ref).exists():
            results["cross_references"]["passed"] += 1
        else:
            results["errors"].append(f"Cross-reference not found: {ref}")
            results["passed"] = False

    for ref_file in (skill_path / "references").glob("*.md"):
        ref_content = ref_file.read_text(encoding="utf-8")
        for ref in extract_file_references(ref_content):
            results["cross_references"]["total"] += 1
            if (skill_path / ref).exists():
                results["cross_references"]["passed"] += 1
            else:
                results["errors"].append(
                    f"Cross-reference in {ref_file.relative_to(skill_path)} "
                    f"not found: {ref}"
                )
                results["passed"] = False

    for rel_path in REQUIRED_EXECUTABLES:
        full_path = skill_path / rel_path
        if not full_path.is_file():
            results["errors"].append(f"Required script missing: {rel_path}")
            results["passed"] = False
        elif not os.access(full_path, os.X_OK):
            results["errors"].append(f"Script is not executable: {rel_path}")
            results["passed"] = False

    if STATIC_PROMPT not in skill_md:
        results["errors"].append(
            f"SKILL.md does not contain the static prompt: {STATIC_PROMPT!r}"
        )
        results["passed"] = False

    transcript_path = skill_path / "templates" / "transcript.md"
    if transcript_path.is_file():
        transcript = transcript_path.read_text(encoding="utf-8")
        if STATIC_PROMPT not in transcript:
            results["errors"].append(
                f"templates/transcript.md does not contain the static prompt: "
                f"{STATIC_PROMPT!r}"
            )
            results["passed"] = False

    return results


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1

    skill_path = Path(sys.argv[1]).resolve()
    if not skill_path.is_dir():
        print(f"Error: '{skill_path}' is not a directory", file=sys.stderr)
        return 1

    results = test_skill(skill_path)

    print(f"Skill: {results['skill_name']}")
    print(f"Tests found: {results['tests_found']}")
    for tag, count in sorted(results["tag_counts"].items()):
        print(f"  {tag}: {count}")
    print(
        f"Files verified: {results['files_verified']['passed']}/"
        f"{results['files_verified']['total']}"
    )
    print(
        f"Cross-references checked: {results['cross_references']['passed']}/"
        f"{results['cross_references']['total']}"
    )
    print(
        f"Assertion format: {results['assertions']['valid']}/"
        f"{results['assertions']['total']} valid"
    )

    if results["errors"]:
        print(f"\nIssues ({len(results['errors'])}):")
        for error in results["errors"]:
            print(f"  - {error}")

    print()
    print(
        "PASS: all checks passed"
        if results["passed"]
        else "FAIL: one or more checks failed"
    )
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
