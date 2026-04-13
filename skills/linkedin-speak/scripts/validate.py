#!/usr/bin/env python3
"""
validate.py - Validate linkedin-speak structure and conventions.
"""

from __future__ import annotations

import json
import os
import re
import sys


def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    if not content.startswith("---"):
        return None, content
    end = content.find("---", 3)
    if end == -1:
        return None, content
    frontmatter_text = content[3:end].strip()
    body = content[end + 3:].strip()
    frontmatter = {}
    for line in frontmatter_text.splitlines():
        match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)', line)
        if match and not line.startswith((" ", "\t")):
            key, value = match.group(1), match.group(2).strip()
            if value and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]
            frontmatter[key] = value
    return frontmatter, body


def extract_file_references(content: str) -> list[str]:
    refs = []
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")
    for pattern in [
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`",
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
    ]:
        for match in re.finditer(pattern, stripped):
            path = match.group(1)
            if not placeholder_re.search(path):
                refs.append(path)
    return sorted(set(refs))


def validate_skill(skill_path: str) -> dict:
    skill_path = os.path.abspath(skill_path)
    skill_md = os.path.join(skill_path, "SKILL.md")
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0}

    if not os.path.isfile(skill_md):
        return {"valid": False, "errors": ["SKILL.md does not exist"], "warnings": warnings, "metrics": metrics}

    with open(skill_md, "r", encoding="utf-8") as handle:
        content = handle.read()

    frontmatter, body = parse_frontmatter(content)
    metrics["skill_md_lines"] = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        if frontmatter.get("name") != os.path.basename(skill_path):
            errors.append("Frontmatter name does not match directory name")
        if not frontmatter.get("description"):
            errors.append("Frontmatter description is missing")

    if body.count("\n") + 1 > 500:
        warnings.append("SKILL.md body exceeds 500 lines")

    for ref in extract_file_references(content):
        if not os.path.exists(os.path.join(skill_path, ref)):
            errors.append(f"Referenced file does not exist: {ref}")

    for required in ["references", "scripts", "templates", "evals", "assets", "agents"]:
        if not os.path.isdir(os.path.join(skill_path, required)):
            warnings.append(f"Missing recommended directory: {required}/")

    refs_dir = os.path.join(skill_path, "references")
    if os.path.isdir(refs_dir):
        metrics["reference_count"] = len([name for name in os.listdir(refs_dir) if name.endswith(".md")])

    valid = not errors
    return {"valid": valid, "errors": errors, "warnings": warnings, "metrics": metrics}


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        raise SystemExit(1)
    result = validate_skill(sys.argv[1])
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
