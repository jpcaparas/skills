#!/usr/bin/env python3
"""
validate.py — Validate the temporal-awareness skill structure and conventions.

Usage:
    python3 validate.py <skill-path>

Output:
    JSON with {valid: bool, errors: [], warnings: [], metrics: {...}}
"""

from __future__ import annotations

import ast
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
    body = content[end + 3 :].strip()
    frontmatter = {}

    for line in frontmatter_text.splitlines():
        if not line.strip() or line.startswith((" ", "\t")):
            continue
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)", line)
        if not match:
            continue
        key = match.group(1)
        value = match.group(2).strip()
        if value and value[0] in {'"', "'"} and value[-1] == value[0]:
            value = value[1:-1]
        frontmatter[key] = value

    return frontmatter, body


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


def has_toc_heading(content: str) -> bool:
    toc_patterns = [
        r"^#+\s+table\s+of\s+contents",
        r"^#+\s+toc\b",
        r"^#+\s+contents\b",
        r"^\-\s+\[.*\]\(#",
    ]
    for line in content.splitlines():
        stripped = line.strip().lower()
        for pattern in toc_patterns:
            if re.match(pattern, stripped):
                return True
    return False


def syntax_check_python(path: str) -> tuple[bool, str | None]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            ast.parse(handle.read(), filename=path)
    except SyntaxError as exc:
        return False, str(exc)
    return True, None


def validate_skill(skill_path: str) -> dict:
    skill_path = os.path.abspath(skill_path)
    errors = []
    warnings = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    skill_md_path = os.path.join(skill_path, "SKILL.md")
    if not os.path.isfile(skill_md_path):
        return {"valid": False, "errors": ["SKILL.md does not exist"], "warnings": warnings, "metrics": metrics}

    with open(skill_md_path, "r", encoding="utf-8") as handle:
        content = handle.read()

    frontmatter, body = parse_frontmatter(content)
    metrics["skill_md_lines"] = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    metrics["total_lines"] = metrics["skill_md_lines"]

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        if frontmatter.get("name") != os.path.basename(skill_path):
            errors.append("Frontmatter name does not match directory name")
        if not frontmatter.get("description"):
            errors.append("Frontmatter missing description")

    if body.count("\n") + 1 > 500:
        warnings.append("SKILL.md body exceeds 500 lines target")

    required_dirs = ["references", "scripts", "templates", "evals", "assets", "agents"]
    for directory in required_dirs:
        path = os.path.join(skill_path, directory)
        if not os.path.isdir(path):
            errors.append(f"Missing directory: {directory}/")

    required_scripts = [
        "capture_temporal_context.py",
        "recency_guard.py",
        "probe_temporal_awareness.py",
        "validate.py",
        "test_skill.py",
    ]
    for script_name in required_scripts:
        script_path = os.path.join(skill_path, "scripts", script_name)
        if not os.path.isfile(script_path):
            errors.append(f"Missing required script: scripts/{script_name}")
            continue
        ok, detail = syntax_check_python(script_path)
        if not ok:
            errors.append(f"Python syntax error in scripts/{script_name}: {detail}")

    refs = extract_file_references(content)
    for ref in refs:
        if not os.path.exists(os.path.join(skill_path, ref)):
            errors.append(f"Referenced file does not exist: {ref}")

    refs_dir = os.path.join(skill_path, "references")
    if os.path.isdir(refs_dir):
        for root, _dirs, files in os.walk(refs_dir):
            for fname in files:
                if fname == ".gitkeep":
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath, "r", encoding="utf-8") as handle:
                    ref_content = handle.read()
                lines = ref_content.count("\n") + (1 if ref_content and not ref_content.endswith("\n") else 0)
                metrics["reference_count"] += 1
                metrics["total_lines"] += lines
                if lines > 1000:
                    errors.append(f"Reference file exceeds 1000 lines: {os.path.relpath(fpath, skill_path)}")
                elif lines > 300 and not has_toc_heading(ref_content):
                    warnings.append(f"Reference file >300 lines without TOC: {os.path.relpath(fpath, skill_path)}")

    evals_path = os.path.join(skill_path, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        errors.append("Missing evals/evals.json")
    else:
        with open(evals_path, "r", encoding="utf-8") as handle:
            evals_data = json.load(handle)
        evals_list = evals_data.get("evals", [])
        tags = {tag for item in evals_list for tag in item.get("tags", [])}
        for tag in ["smoke", "edge", "negative", "disclosure"]:
            if tag not in tags:
                errors.append(f"Missing eval coverage for tag: {tag}")

    return {"valid": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        raise SystemExit(1)

    result = validate_skill(sys.argv[1])
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
