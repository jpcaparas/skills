#!/usr/bin/env python3
"""Validate the product-question skill structure and conventions."""

from __future__ import annotations

import ast
import json
import os
import re
import sys


REQUIRED_DIRS = ["references", "scripts", "templates", "evals", "assets", "agents"]
REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "agents/openai.yaml",
    "templates/product-answer.md",
    "evals/evals.json",
]
REQUIRED_REFERENCES = [
    "references/README.md",
    "references/discovery.md",
    "references/answer-contract.md",
    "references/gotchas.md",
]
REQUIRED_SCRIPTS = ["scripts/validate.py", "scripts/test_skill.py"]
REQUIRED_TAGS = ["smoke", "edge", "negative", "disclosure"]
CONTENT_TERMS = [
    "share-ready",
    "product",
    "PM",
    "stakeholder",
    "plain-English",
    "codebase",
    "Confidence",
]


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    if not content.startswith("---"):
        return None, content
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", content, re.DOTALL)
    if not match:
        return None, content
    frontmatter_text = match.group(1)
    body = match.group(2)
    frontmatter: dict[str, str] = {}
    for line in frontmatter_text.splitlines():
        if not line.strip() or line.startswith((" ", "\t")):
            continue
        m = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$", line)
        if not m:
            continue
        key = m.group(1)
        value = m.group(2).strip()
        if value and value[0] in {'"', "'"} and value[-1] == value[0]:
            value = value[1:-1]
        frontmatter[key] = value
    return frontmatter, body


def extract_file_references(content: str) -> list[str]:
    refs: list[str] = []
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|\s")
    patterns = [
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`",
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
    ]
    for pattern in patterns:
        for path in re.findall(pattern, stripped):
            if not placeholder_re.search(path):
                refs.append(path)
    return sorted(set(refs))


def syntax_check_python(path: str) -> tuple[bool, str | None]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            ast.parse(handle.read(), filename=path)
    except SyntaxError as exc:
        return False, str(exc)
    return True, None


def line_count(path: str) -> int:
    with open(path, "r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def validate_skill(skill_path: str) -> dict:
    skill_path = os.path.abspath(skill_path)
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    skill_md_path = os.path.join(skill_path, "SKILL.md")
    if not os.path.isfile(skill_md_path):
        return {"valid": False, "errors": ["SKILL.md does not exist"], "warnings": warnings, "metrics": metrics}

    skill_content = open(skill_md_path, "r", encoding="utf-8").read()
    frontmatter, body = parse_frontmatter(skill_content)
    metrics["skill_md_lines"] = skill_content.count("\n") + (1 if skill_content and not skill_content.endswith("\n") else 0)
    metrics["total_lines"] = metrics["skill_md_lines"]

    if frontmatter is None:
        errors.append("SKILL.md is missing YAML frontmatter")
    else:
        if frontmatter.get("name") != os.path.basename(skill_path):
            errors.append("Frontmatter name does not match the directory name")
        description = frontmatter.get("description", "")
        if not description:
            errors.append("Frontmatter description is missing")
        if len(description) > 1024:
            errors.append("Frontmatter description exceeds 1024 characters")
        for term in ["product", "PM", "stakeholder", "share-ready"]:
            if term not in description:
                errors.append(f"Frontmatter description must mention {term!r}")

    if body.count("\n") + 1 > 500:
        warnings.append("SKILL.md body exceeds 500 lines target")

    for directory in REQUIRED_DIRS:
        if not os.path.isdir(os.path.join(skill_path, directory)):
            errors.append(f"Missing directory: {directory}/")

    for relpath in REQUIRED_FILES + REQUIRED_REFERENCES + REQUIRED_SCRIPTS:
        if not os.path.exists(os.path.join(skill_path, relpath)):
            errors.append(f"Missing required file: {relpath}")

    for relpath in REQUIRED_SCRIPTS:
        script_path = os.path.join(skill_path, relpath)
        if os.path.isfile(script_path):
            ok, detail = syntax_check_python(script_path)
            if not ok:
                errors.append(f"Python syntax error in {relpath}: {detail}")

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
        content = open(markdown_path, "r", encoding="utf-8").read()
        for ref in extract_file_references(content):
            if not os.path.exists(os.path.join(skill_path, ref)):
                errors.append(f"Referenced file does not exist: {ref}")
        if markdown_path != skill_md_path:
            lines = line_count(markdown_path)
            metrics["reference_count"] += 1
            metrics["total_lines"] += lines
            if lines > 1000:
                errors.append(f"Markdown file exceeds 1000 lines: {os.path.relpath(markdown_path, skill_path)}")

    missing_terms = [term for term in CONTENT_TERMS if term not in skill_content]
    if missing_terms:
        errors.append("SKILL.md is missing required content terms: " + ", ".join(missing_terms))

    evals_path = os.path.join(skill_path, "evals", "evals.json")
    if os.path.isfile(evals_path):
        try:
            data = json.loads(open(evals_path, "r", encoding="utf-8").read())
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is not valid JSON: {exc}")
        else:
            if data.get("skill_name") != os.path.basename(skill_path):
                errors.append("evals/evals.json skill_name must match the directory name")
            tags = {tag for item in data.get("evals", []) for tag in item.get("tags", [])}
            for tag in REQUIRED_TAGS:
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
