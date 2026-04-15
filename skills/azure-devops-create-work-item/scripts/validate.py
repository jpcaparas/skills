#!/usr/bin/env python3
"""
validate.py — Validate a skill's structure and conventions.

Usage:
    python3 validate.py <skill-path>

Output:
    JSON with {valid: bool, errors: [], warnings: [], metrics: {...}}

Exit codes:
    0 = valid (may have warnings)
    1 = invalid (has errors)
"""

from __future__ import annotations

import json
import os
import re
import sys


def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return None, content

    end = content.find("---", 3)
    if end == -1:
        return None, content

    frontmatter_text = content[3:end].strip()
    body = content[end + 3:].strip()

    fm = {}
    current_key = None
    for line in frontmatter_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)', line)
        if match and not line.startswith(" ") and not line.startswith("\t"):
            key = match.group(1)
            value = match.group(2).strip()
            if value and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]
            fm[key] = value
            current_key = key
            continue

        if current_key and (line.startswith("  ") or line.startswith("\t")):
            continue

    return fm, body


def count_lines(filepath: str) -> int:
    try:
        with open(filepath, "r", encoding="utf-8") as handle:
            return sum(1 for _ in handle)
    except (OSError, UnicodeDecodeError):
        return 0


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


def has_toc_heading(content: str) -> bool:
    toc_patterns = [
        r"^#+\s+table\s+of\s+contents",
        r"^#+\s+toc\b",
        r"^#+\s+contents\b",
        r"^\-\s+\[.*\]\(#",
    ]
    for line in content.split("\n"):
        stripped = line.strip().lower()
        for pattern in toc_patterns:
            if re.match(pattern, stripped):
                return True
    return False


def validate_skill(skill_path: str) -> dict:
    errors = []
    warnings = []
    metrics = {
        "skill_md_lines": 0,
        "reference_count": 0,
        "total_lines": 0,
    }

    skill_path = os.path.abspath(skill_path)
    dir_name = os.path.basename(skill_path)

    skill_md_path = os.path.join(skill_path, "SKILL.md")
    if not os.path.isfile(skill_md_path):
        errors.append("SKILL.md does not exist")
        return {"valid": False, "errors": errors, "warnings": warnings, "metrics": metrics}

    with open(skill_md_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    skill_md_lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    metrics["skill_md_lines"] = skill_md_lines
    metrics["total_lines"] = skill_md_lines

    frontmatter, body = parse_frontmatter(content)

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter (must start with ---)")
    else:
        name = frontmatter.get("name", "")
        if not name:
            errors.append("Frontmatter missing required 'name' field")
        else:
            if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", name):
                errors.append(
                    f"name '{name}' is invalid: must be lowercase letters, digits, "
                    "and hyphens (1-64 chars, must start/end with alphanumeric)"
                )
            elif len(name) > 64:
                errors.append(f"name '{name}' exceeds 64 character limit ({len(name)} chars)")
            if name != dir_name:
                errors.append(f"name '{name}' does not match directory name '{dir_name}'")

        description = frontmatter.get("description", "")
        if not description:
            errors.append("Frontmatter missing required 'description' field")
        elif len(description) > 1024:
            errors.append(f"description exceeds 1024 chars ({len(description)} chars)")

    body_lines = body.count("\n") + (1 if body and not body.endswith("\n") else 0)
    if body_lines > 500:
        warnings.append(
            f"SKILL.md body is {body_lines} lines (target: <500). "
            "Consider moving content to references."
        )

    refs = extract_file_references(content)
    for ref in refs:
        ref_path = os.path.join(skill_path, ref)
        if not os.path.exists(ref_path):
            errors.append(f"Referenced file does not exist: {ref}")

    refs_dir = os.path.join(skill_path, "references")
    if os.path.isdir(refs_dir):
        for root, _, files in os.walk(refs_dir):
            for fname in files:
                if fname == ".gitkeep":
                    continue
                fpath = os.path.join(root, fname)
                lines = count_lines(fpath)
                metrics["reference_count"] += 1
                metrics["total_lines"] += lines

                if lines > 1000:
                    errors.append(
                        f"Reference file exceeds 1000 lines: "
                        f"{os.path.relpath(fpath, skill_path)} ({lines} lines)"
                    )
                elif lines > 300:
                    try:
                        with open(fpath, "r", encoding="utf-8") as handle:
                            file_content = handle.read()
                        if not has_toc_heading(file_content):
                            warnings.append(
                                f"Reference file >300 lines without TOC: "
                                f"{os.path.relpath(fpath, skill_path)} ({lines} lines)"
                            )
                    except (OSError, UnicodeDecodeError):
                        pass

    required_dirs = ["references", "scripts", "templates", "evals", "assets", "agents"]
    for directory in required_dirs:
        dpath = os.path.join(skill_path, directory)
        if not os.path.isdir(dpath):
            warnings.append(f"Missing recommended directory: {directory}/")
        else:
            contents = [name for name in os.listdir(dpath) if name != ".gitkeep"]
            if not contents:
                gitkeep = os.path.join(dpath, ".gitkeep")
                if not os.path.exists(gitkeep):
                    warnings.append(f"Empty directory without .gitkeep: {directory}/")

    evals_path = os.path.join(skill_path, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        warnings.append("evals/evals.json not found (recommended for all production skills)")
    else:
        try:
            with open(evals_path, "r", encoding="utf-8") as handle:
                evals_data = json.load(handle)
            if not isinstance(evals_data.get("evals"), list):
                warnings.append("evals/evals.json: 'evals' field should be an array")
            elif len(evals_data["evals"]) == 0:
                warnings.append("evals/evals.json: no test cases defined (array is empty)")
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is not valid JSON: {exc}")

    scripts_dir = os.path.join(skill_path, "scripts")
    if os.path.isdir(scripts_dir):
        for fname in os.listdir(scripts_dir):
            if fname == ".gitkeep":
                continue
            fpath = os.path.join(scripts_dir, fname)
            if os.path.isfile(fpath):
                metrics["total_lines"] += count_lines(fpath)

    valid = len(errors) == 0
    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        sys.exit(1)

    skill_path = sys.argv[1]
    if not os.path.isdir(skill_path):
        print(f"Error: '{skill_path}' is not a directory", file=sys.stderr)
        sys.exit(1)

    result = validate_skill(skill_path)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
