#!/usr/bin/env python3
"""Validate the reading-notes skill package."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


REQUIRED_DIRS = ["references", "scripts", "templates", "evals", "assets", "agents"]
REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "agents/openai.yaml",
    "references/intake.md",
    "references/synthesis.md",
    "references/output-formats.md",
    "references/gotchas.md",
    "templates/reading-notes.md",
    "scripts/probe_reading_notes.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "evals/evals.json",
    "assets/.gitkeep",
]
REQUIRED_EVAL_TAGS = {"smoke", "edge", "negative", "disclosure"}


def count_lines(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    if not content.startswith("---"):
        return None, content
    end = content.find("---", 3)
    if end == -1:
        return None, content
    raw = content[3:end].strip()
    body = content[end + 3 :].strip()
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.startswith((" ", "\t", "#")):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if value and value[0] in {"'", '"'} and value[-1] == value[0]:
            value = value[1:-1]
        data[key] = value
    return data, body


def extract_file_references(content: str) -> list[str]:
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    refs: set[str] = set()
    placeholder_re = re.compile(r"[{}<>]|\s")
    patterns = [
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`",
        r"\[[^\]]+\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, stripped):
            candidate = match.group(1)
            if not placeholder_re.search(candidate):
                refs.add(candidate)
    return sorted(refs)


def syntax_check_python(path: Path) -> str | None:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return str(exc)
    return None


def validate_skill(skill_path: str | Path) -> dict[str, Any]:
    root = Path(skill_path).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    for directory in REQUIRED_DIRS:
        if not (root / directory).is_dir():
            errors.append(f"Missing directory: {directory}/")

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"Missing required file: {relative}")

    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        return {"valid": False, "errors": errors, "warnings": warnings, "metrics": metrics}

    content = skill_md.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    metrics["skill_md_lines"] = count_lines(skill_md)
    metrics["total_lines"] += metrics["skill_md_lines"]

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        name = frontmatter.get("name", "")
        if name != root.name:
            errors.append(f"Frontmatter name '{name}' does not match directory '{root.name}'")
        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", name):
            errors.append(f"Frontmatter name '{name}' is not a valid skill name")
        description = frontmatter.get("description", "")
        if not description:
            errors.append("Frontmatter missing description")
        elif len(description) > 1024:
            errors.append(f"Frontmatter description exceeds 1024 characters ({len(description)})")

    if body.count("\n") + 1 > 500:
        warnings.append("SKILL.md body exceeds 500 lines")

    for relative in extract_file_references(content):
        if not (root / relative).exists():
            errors.append(f"Referenced file does not exist: {relative}")

    for reference in sorted((root / "references").glob("*.md")):
        ref_content = reference.read_text(encoding="utf-8")
        lines = count_lines(reference)
        metrics["reference_count"] += 1
        metrics["total_lines"] += lines
        if lines > 1000:
            errors.append(f"Reference file exceeds 1000 lines: {reference.relative_to(root)}")
        for relative in extract_file_references(ref_content):
            if not (root / relative).exists():
                errors.append(f"Referenced file does not exist in {reference.relative_to(root)}: {relative}")

    metadata = root / "metadata.json"
    if metadata.is_file():
        try:
            json.loads(metadata.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"metadata.json is not valid JSON: {exc}")

    evals_path = root / "evals" / "evals.json"
    if evals_path.is_file():
        try:
            evals = json.loads(evals_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is not valid JSON: {exc}")
        else:
            seen_tags = {tag for item in evals.get("evals", []) for tag in item.get("tags", [])}
            missing_tags = sorted(REQUIRED_EVAL_TAGS - seen_tags)
            for tag in missing_tags:
                errors.append(f"Missing eval coverage for tag: {tag}")

    for relative in REQUIRED_FILES:
        path = root / relative
        if path.suffix == ".py" and path.is_file():
            syntax_error = syntax_check_python(path)
            if syntax_error:
                errors.append(f"Python syntax error in {relative}: {syntax_error}")

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
