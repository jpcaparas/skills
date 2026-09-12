#!/usr/bin/env python3
"""
validate.py - Validate a skill's structure and conventions.

Usage:
    python3 validate.py <skill-path>
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


def count_lines(path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)
    except OSError:
        return 0


def extract_file_references(content: str) -> list[str]:
    refs = []
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")
    patterns = [
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`",
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)"
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, stripped):
            path = match.group(1)
            if not placeholder_re.search(path):
                refs.append(path)
    return sorted(set(refs))


def has_toc_heading(content: str) -> bool:
    toc_patterns = [
        r"^#+\s+table\s+of\s+contents",
        r"^#+\s+toc\b",
        r"^#+\s+contents\b",
        r"^\-\s+\[.*\]\(#"
    ]
    for line in content.splitlines():
        lowered = line.strip().lower()
        for pattern in toc_patterns:
            if re.match(pattern, lowered):
                return True
    return False


def validate_skill(skill_path: str) -> dict:
    errors = []
    warnings = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    skill_path = os.path.abspath(skill_path)
    dir_name = os.path.basename(skill_path)
    skill_md = os.path.join(skill_path, "SKILL.md")

    if not os.path.isfile(skill_md):
        return {"valid": False, "errors": ["SKILL.md does not exist"], "warnings": warnings, "metrics": metrics}

    with open(skill_md, "r", encoding="utf-8") as handle:
        content = handle.read()

    frontmatter, body = parse_frontmatter(content)
    body_lines = body.count("\n") + (1 if body and not body.endswith("\n") else 0)
    metrics["skill_md_lines"] = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    metrics["total_lines"] = metrics["skill_md_lines"]

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        name = frontmatter.get("name", "")
        description = frontmatter.get("description", "")
        if not name:
            errors.append("Frontmatter missing required 'name' field")
        elif not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", name):
            errors.append("Frontmatter 'name' must be lowercase letters, digits, and hyphens")
        elif name != dir_name:
            errors.append(f"name '{name}' does not match directory name '{dir_name}'")
        if not description:
            errors.append("Frontmatter missing required 'description' field")
        elif len(description) > 1024:
            errors.append("Frontmatter 'description' exceeds 1024 characters")

    if body_lines > 500:
        warnings.append(f"SKILL.md body is {body_lines} lines; move content into references if needed")

    for ref in extract_file_references(content):
        if not os.path.exists(os.path.join(skill_path, ref)):
            errors.append(f"Referenced file does not exist: {ref}")

    for required_dir in ["references", "scripts", "templates", "evals", "assets", "agents"]:
        dir_path = os.path.join(skill_path, required_dir)
        if not os.path.isdir(dir_path):
            warnings.append(f"Missing recommended directory: {required_dir}/")
        elif not [entry for entry in os.listdir(dir_path) if entry != ".gitkeep"] and not os.path.exists(os.path.join(dir_path, ".gitkeep")):
            warnings.append(f"Empty directory without .gitkeep: {required_dir}/")

    refs_dir = os.path.join(skill_path, "references")
    if os.path.isdir(refs_dir):
        for root, _, files in os.walk(refs_dir):
            for filename in files:
                if filename == ".gitkeep":
                    continue
                path = os.path.join(root, filename)
                lines = count_lines(path)
                metrics["reference_count"] += 1
                metrics["total_lines"] += lines
                if lines > 1000:
                    errors.append(f"Reference file exceeds 1000 lines: {os.path.relpath(path, skill_path)}")
                elif lines > 300:
                    with open(path, "r", encoding="utf-8") as handle:
                        if not has_toc_heading(handle.read()):
                            warnings.append(f"Reference file >300 lines without TOC: {os.path.relpath(path, skill_path)}")

    evals_path = os.path.join(skill_path, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        warnings.append("evals/evals.json not found")
    else:
        try:
            with open(evals_path, "r", encoding="utf-8") as handle:
                evals = json.load(handle)
            if not isinstance(evals.get("evals"), list):
                warnings.append("evals/evals.json: 'evals' should be an array")
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is not valid JSON: {exc}")

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
