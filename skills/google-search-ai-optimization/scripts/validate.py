#!/usr/bin/env python3
"""Validate the google-search-ai-optimization skill structure."""

from __future__ import annotations

import ast
import json
import os
import re
import sys


REQUIRED_DIRS = ["references", "scripts", "templates", "evals", "assets", "agents"]
REQUIRED_REFERENCES = [
    "references/README.md",
    "references/google-guidance.md",
    "references/technical-implementation.md",
    "references/content-and-entity-patterns.md",
    "references/ecommerce-local-agentic.md",
    "references/gotchas.md",
]
REQUIRED_SCRIPTS = ["audit_page.py", "validate.py", "test_skill.py"]
REQUIRED_TEMPLATES = ["templates/implementation-brief-template.md"]


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    if not content.startswith("---"):
        return None, content
    end = content.find("---", 3)
    if end == -1:
        return None, content
    frontmatter_text = content[3:end].strip()
    body = content[end + 3 :].strip()
    frontmatter: dict[str, str] = {}
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
    refs: list[str] = []
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


def line_count(path: str) -> int:
    with open(path, "r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def syntax_check_python(path: str) -> tuple[bool, str]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            ast.parse(handle.read(), filename=path)
    except SyntaxError as exc:
        return False, str(exc)
    return True, ""


def validate_skill(skill_path: str) -> dict:
    skill_path = os.path.abspath(skill_path)
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    skill_md = os.path.join(skill_path, "SKILL.md")
    if not os.path.isfile(skill_md):
        return {"valid": False, "errors": ["SKILL.md does not exist"], "warnings": warnings, "metrics": metrics}

    content = open(skill_md, "r", encoding="utf-8").read()
    frontmatter, body = parse_frontmatter(content)
    metrics["skill_md_lines"] = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    metrics["total_lines"] = metrics["skill_md_lines"]

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        name = frontmatter.get("name", "")
        if name != os.path.basename(skill_path):
            errors.append(f"Frontmatter name '{name}' does not match directory")
        description = frontmatter.get("description", "")
        if not description:
            errors.append("Frontmatter missing description")
        elif len(description) > 1024:
            errors.append("Description exceeds 1024 characters")

    if body.count("\n") + 1 > 500:
        warnings.append("SKILL.md body exceeds 500 lines target")

    for directory in REQUIRED_DIRS:
        if not os.path.isdir(os.path.join(skill_path, directory)):
            errors.append(f"Missing directory: {directory}/")

    for ref in REQUIRED_REFERENCES + REQUIRED_TEMPLATES:
        if not os.path.isfile(os.path.join(skill_path, ref)):
            errors.append(f"Missing required file: {ref}")

    for script in REQUIRED_SCRIPTS:
        script_path = os.path.join(skill_path, "scripts", script)
        if not os.path.isfile(script_path):
            errors.append(f"Missing required script: scripts/{script}")
            continue
        ok, detail = syntax_check_python(script_path)
        if not ok:
            errors.append(f"Python syntax error in scripts/{script}: {detail}")

    for ref in extract_file_references(content):
        if not os.path.exists(os.path.join(skill_path, ref)):
            errors.append(f"Referenced file does not exist: {ref}")

    for root, _dirs, files in os.walk(os.path.join(skill_path, "references")):
        for filename in files:
            if filename == ".gitkeep":
                continue
            path = os.path.join(root, filename)
            count = line_count(path)
            metrics["reference_count"] += 1
            metrics["total_lines"] += count
            if count > 1000:
                errors.append(f"Reference file exceeds 1000 lines: {os.path.relpath(path, skill_path)}")

    evals_path = os.path.join(skill_path, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        errors.append("Missing evals/evals.json")
    else:
        try:
            evals = json.loads(open(evals_path, "r", encoding="utf-8").read()).get("evals", [])
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is invalid JSON: {exc}")
            evals = []
        tags = {tag for item in evals for tag in item.get("tags", [])}
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
