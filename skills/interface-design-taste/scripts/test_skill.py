#!/usr/bin/env python3
"""
test_skill.py - Validate packaging and content coverage for interface-design-taste.

Usage:
    python3 test_skill.py <skill-path>
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


STYLE_FAMILIES = [
    "Editorial Calm",
    "Product Precision",
    "Warm Material",
    "Operational Density",
    "Expressive Showcase",
]


def extract_file_references(content: str) -> list[str]:
    refs: list[str] = []
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    patterns = [
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`\s]+)`",
        r"\((?:\./)?((?:references|scripts|templates|assets|agents|evals)/[^)\s]+)\)",
    ]
    for pattern in patterns:
        refs.extend(re.findall(pattern, stripped))
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
    checks = [
        ("covers-web-app-desktop", all(word in skill_content.lower() for word in ["web", "app", "desktop"])),
        ("mentions-platform-adaptation", "references/platform-adaptation.md" in skill_content),
        ("mentions-critique-workflow", "references/critique-workflow.md" in skill_content),
        ("mentions-design-systems", "references/design-systems-and-tokens.md" in skill_content),
    ]

    family_content = Path(os.path.join(skill_path, "references", "style-families.md")).read_text(encoding="utf-8")
    checks.extend((f"family-{family.lower().replace(' ', '-')}", family in family_content) for family in STYLE_FAMILIES)

    platform_content = Path(os.path.join(skill_path, "references", "platform-adaptation.md")).read_text(encoding="utf-8")
    checks.extend(
        [
            ("platform-web-marketing", "## Web Marketing" in platform_content),
            ("platform-web-application", "## Web Application" in platform_content),
            ("platform-desktop-application", "## Desktop Application" in platform_content),
        ]
    )

    gotchas_content = Path(os.path.join(skill_path, "references", "gotchas.md")).read_text(encoding="utf-8")
    checks.append(("gotchas-count", len(re.findall(r"^\d+\.\s+\*\*", gotchas_content, re.MULTILINE)) >= 10))

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

