#!/usr/bin/env python3
"""
validate.py - Validate the tarsier skill structure and conventions.

Usage:
    python3 validate.py <skill-path>

Exit codes:
    0 = valid
    1 = invalid
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


REQUIRED_DIRS = ["references", "scripts", "templates", "evals", "assets", "agents"]
REQUIRED_FILES = [
    "README.md",
    "metadata.json",
    "scripts/rasterize.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "templates/transcript.md",
    "evals/evals.json",
]
REQUIRED_EVAL_TAGS = ["smoke", "edge", "negative"]


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    if not content.startswith("---"):
        return None, content

    end = content.find("---", 3)
    if end == -1:
        return None, content

    frontmatter_text = content[3:end].strip()
    body = content[end + 3 :].strip()
    data: dict[str, str] = {}

    for line in frontmatter_text.splitlines():
        if not line.strip() or line.startswith((" ", "\t", "#")):
            continue
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$", line)
        if not match:
            continue
        key = match.group(1)
        value = match.group(2).strip()
        if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
            value = value[1:-1]
        data[key] = value

    return data, body


def extract_file_references(content: str) -> list[str]:
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")
    refs: set[str] = set()

    for match in re.finditer(
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`", stripped
    ):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.add(path)

    for match in re.finditer(
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
        stripped,
    ):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.add(path)

    return sorted(refs)


def syntax_check_python(path: Path) -> str | None:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return str(exc)
    return None


def validate_skill(skill_path: str) -> dict[str, object]:
    root = Path(skill_path).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        return {
            "valid": False,
            "errors": ["SKILL.md does not exist"],
            "warnings": warnings,
            "metrics": metrics,
        }

    content = skill_md.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    metrics["skill_md_lines"] = content.count("\n") + (
        1 if content and not content.endswith("\n") else 0
    )
    metrics["total_lines"] = metrics["skill_md_lines"]

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        name = frontmatter.get("name", "")
        if not name:
            errors.append("Frontmatter missing required 'name' field")
        elif name != root.name:
            errors.append(
                f"name '{name}' does not match directory name '{root.name}'"
            )

        description = frontmatter.get("description", "")
        if not description:
            errors.append("Frontmatter missing required 'description' field")
        elif len(description) > 1024:
            errors.append(
                f"description exceeds 1024 chars ({len(description)} chars)"
            )

    body_lines = body.count("\n") + (1 if body and not body.endswith("\n") else 0)
    if body_lines > 500:
        warnings.append(f"SKILL.md body exceeds 500 lines target ({body_lines} lines)")

    for directory in REQUIRED_DIRS:
        if not (root / directory).is_dir():
            errors.append(f"Missing required directory: {directory}/")

    for rel_path in REQUIRED_FILES:
        if not (root / rel_path).exists():
            errors.append(f"Missing required file: {rel_path}")

    for rel_path in extract_file_references(content):
        if not (root / rel_path).exists():
            errors.append(f"Referenced file does not exist: {rel_path}")

    for rel_path in ["scripts/rasterize.py", "scripts/validate.py", "scripts/test_skill.py"]:
        script_path = root / rel_path
        if script_path.is_file():
            syntax_error = syntax_check_python(script_path)
            if syntax_error:
                errors.append(f"Python syntax error in {rel_path}: {syntax_error}")

    metadata_path = root / "metadata.json"
    if metadata_path.is_file():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"metadata.json is not valid JSON: {exc}")
        else:
            if metadata.get("name") != root.name:
                errors.append(
                    f"metadata.json name '{metadata.get('name')}' does not match "
                    f"directory name '{root.name}'"
                )

    evals_path = root / "evals" / "evals.json"
    if evals_path.is_file():
        try:
            evals_data = json.loads(evals_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is not valid JSON: {exc}")
        else:
            evals = evals_data.get("evals", [])
            if not isinstance(evals, list) or not evals:
                errors.append("evals/evals.json must contain a non-empty 'evals' array")
            else:
                tags = {tag for item in evals for tag in item.get("tags", [])}
                for required_tag in REQUIRED_EVAL_TAGS:
                    if required_tag not in tags:
                        errors.append(f"Missing eval coverage for tag: {required_tag}")

    refs_root = root / "references"
    if refs_root.is_dir():
        for ref_path in refs_root.rglob("*"):
            if ref_path.is_file() and not ref_path.name.startswith("."):
                metrics["reference_count"] += 1
                metrics["total_lines"] += (
                    ref_path.read_text(encoding="utf-8").count("\n") + 1
                )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        return 1

    skill_path = Path(sys.argv[1]).resolve()
    if not skill_path.is_dir():
        print(f"Error: '{skill_path}' is not a directory", file=sys.stderr)
        return 1

    result = validate_skill(str(skill_path))
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
