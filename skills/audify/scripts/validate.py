#!/usr/bin/env python3
"""Validate audify structure, cross-references, and placeholder hygiene."""

from __future__ import annotations

import json
import os
import re
import sys


REQUIRED_FILES = [
    "SKILL.md",
    "references/api.md",
    "references/configuration.md",
    "references/patterns.md",
    "references/gotchas.md",
    "scripts/audify.py",
    "scripts/probe_gemini_tts.py",
    "scripts/test_audify_unit.py",
    "scripts/test_skill.py",
    "evals/evals.json",
]


def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    if not content.startswith("---"):
        return None, content
    end = content.find("---", 3)
    if end == -1:
        return None, content
    frontmatter_text = content[3:end].strip()
    body = content[end + 3 :].strip()
    result = {}
    for line in frontmatter_text.splitlines():
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if value and value[0] in {"'", '"'} and value[-1] == value[0]:
            value = value[1:-1]
        result[key] = value
    return result, body


def extract_file_references(content: str) -> list[str]:
    refs = []
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")
    for match in re.finditer(r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`", stripped):
        candidate = match.group(1)
        if not placeholder_re.search(candidate):
            refs.append(candidate)
    for match in re.finditer(r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)", stripped):
        candidate = match.group(1)
        if not placeholder_re.search(candidate):
            refs.append(candidate)
    return sorted(set(refs))


def count_lines(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def validate_skill(skill_path: str) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    skill_path = os.path.abspath(skill_path)
    dir_name = os.path.basename(skill_path)

    for relative in REQUIRED_FILES:
        if not os.path.exists(os.path.join(skill_path, relative)):
            errors.append(f"Required file missing: {relative}")

    skill_md_path = os.path.join(skill_path, "SKILL.md")
    if not os.path.isfile(skill_md_path):
        return {"valid": False, "errors": errors, "warnings": warnings, "metrics": metrics}

    content = open(skill_md_path, "r", encoding="utf-8").read()
    metrics["skill_md_lines"] = count_lines(skill_md_path)
    metrics["total_lines"] = metrics["skill_md_lines"]
    frontmatter, body = parse_frontmatter(content)

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        if frontmatter.get("name") != dir_name:
            errors.append(f"Frontmatter name must match directory name '{dir_name}'")
        if not frontmatter.get("description"):
            errors.append("Frontmatter missing description")

    if body.count("\n") + 1 > 500:
        warnings.append("SKILL.md body exceeds 500 lines")

    if "{{" in content or "TODO:" in content:
        errors.append("SKILL.md still contains template placeholders or TODO markers")

    refs = extract_file_references(content)
    for ref in refs:
        if not os.path.exists(os.path.join(skill_path, ref)):
            errors.append(f"Cross-reference missing: {ref}")

    for root, _dirs, files in os.walk(os.path.join(skill_path, "references")):
        for name in files:
            if not name.endswith(".md"):
                continue
            path = os.path.join(root, name)
            metrics["reference_count"] += 1
            metrics["total_lines"] += count_lines(path)
            ref_content = open(path, "r", encoding="utf-8").read()
            if "{{" in ref_content or "TODO:" in ref_content:
                errors.append(f"Reference still contains template placeholders: {os.path.relpath(path, skill_path)}")
            for ref in extract_file_references(ref_content):
                if not os.path.exists(os.path.join(skill_path, ref)):
                    errors.append(f"Cross-reference missing in {os.path.relpath(path, skill_path)}: {ref}")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        raise SystemExit(1)
    result = validate_skill(sys.argv[1])
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
