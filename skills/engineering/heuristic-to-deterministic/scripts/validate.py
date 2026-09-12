#!/usr/bin/env python3
"""Validate the heuristic-to-deterministic skill package."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


REQUIRED_DIRS = ["references", "scripts", "templates", "evals", "assets", "agents"]
REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "references/conversion-patterns.md",
    "references/verification.md",
    "references/gotchas.md",
    "scripts/classify_conversion.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "evals/evals.json",
    "templates/.gitkeep",
    "assets/.gitkeep",
    "agents/.gitkeep",
]
REQUIRED_TAGS = {"smoke", "edge", "negative", "disclosure"}


def line_count(path: Path) -> int:
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
    frontmatter: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.startswith((" ", "\t")):
            continue
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
            value = value[1:-1]
        frontmatter[key] = value
    return frontmatter, body


def extract_file_references(content: str) -> list[str]:
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    refs: set[str] = set()
    for pattern in [
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`",
        r"\[[^\]]+\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
    ]:
        for match in re.finditer(pattern, stripped):
            candidate = match.group(1)
            if not re.search(r"[{}<>]|\s", candidate):
                refs.add(candidate)
    return sorted(refs)


def syntax_check_python(path: Path) -> str | None:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return str(exc)
    return None


def validate_skill(skill_path: str | Path) -> dict[str, object]:
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
    metrics["skill_md_lines"] = line_count(skill_md)
    metrics["total_lines"] += metrics["skill_md_lines"]

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        if frontmatter.get("name") != root.name:
            errors.append("Frontmatter name must match directory name")
        description = frontmatter.get("description", "")
        for fragment in ["deterministic", "validator", "normalizer", "Do NOT"]:
            if fragment not in description:
                errors.append(f"Frontmatter description must mention {fragment!r}")
        if len(description) > 1024:
            errors.append("Frontmatter description exceeds 1024 characters")

    if body.count("\n") + 1 > 500:
        warnings.append("SKILL.md body exceeds 500 lines")

    for relative in extract_file_references(content):
        if not (root / relative).exists():
            errors.append(f"Cross-reference missing: {relative}")

    refs_root = root / "references"
    if refs_root.is_dir():
        for path in sorted(refs_root.glob("*.md")):
            ref_content = path.read_text(encoding="utf-8")
            for relative in extract_file_references(ref_content):
                if not (root / relative).exists():
                    errors.append(f"Cross-reference missing in {path.relative_to(root)}: {relative}")
            lines = line_count(path)
            metrics["reference_count"] += 1
            metrics["total_lines"] += lines
            if lines > 1000:
                errors.append(f"Reference file exceeds 1000 lines: {path.relative_to(root)}")

    for relative in REQUIRED_FILES:
        path = root / relative
        if path.suffix == ".py" and path.is_file():
            syntax_error = syntax_check_python(path)
            if syntax_error:
                errors.append(f"Python syntax error in {relative}: {syntax_error}")

    metadata_path = root / "metadata.json"
    if metadata_path.is_file():
        try:
            json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid metadata.json: {exc}")

    evals_path = root / "evals" / "evals.json"
    if evals_path.is_file():
        try:
            evals = json.loads(evals_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Invalid evals/evals.json: {exc}")
        else:
            tags = {tag for item in evals.get("evals", []) for tag in item.get("tags", [])}
            missing_tags = sorted(REQUIRED_TAGS - tags)
            for tag in missing_tags:
                errors.append(f"Missing eval coverage for tag: {tag}")

    placeholder_marker = "TO" + "DO:"
    for relative in REQUIRED_FILES:
        path = root / relative
        if path.is_file() and placeholder_marker in path.read_text(encoding="utf-8", errors="ignore"):
            errors.append(f"Template placeholder found in {relative}")

    return {"valid": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        return 1
    result = validate_skill(sys.argv[1])
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
