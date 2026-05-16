#!/usr/bin/env python3
"""
Validate the zoom-out skill package.
"""

from __future__ import annotations

import json
import os
import py_compile
import re
import sys
from pathlib import Path
from typing import Any


REQUIRED_DIRS = ["references", "scripts", "templates", "evals", "assets", "agents"]


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    if not content.startswith("---\n"):
        return None, content
    end = content.find("\n---", 4)
    if end == -1:
        return None, content
    raw = content[4:end].strip()
    body = content[end + 4 :].strip()
    frontmatter: dict[str, str] = {}
    for line in raw.splitlines():
        if not line.strip() or line.startswith(" ") or line.startswith("\t"):
            continue
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
            value = value[1:-1]
        frontmatter[key] = value
    return frontmatter, body


def count_lines(path: Path) -> int:
    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeDecodeError):
        return 0


def extract_file_references(content: str) -> list[str]:
    refs: set[str] = set()
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|\s")
    pattern = r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`"
    for match in re.finditer(pattern, stripped):
        value = match.group(1)
        if not placeholder_re.search(value):
            refs.add(value)
    link_pattern = r"\[[^\]]+\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)"
    for match in re.finditer(link_pattern, stripped):
        value = match.group(1)
        if not placeholder_re.search(value):
            refs.add(value)
    return sorted(refs)


def has_toc(content: str) -> bool:
    lowered = content.lower()
    return "## table of contents" in lowered or "## contents" in lowered


def validate_skill(skill_path: str) -> dict[str, Any]:
    root = Path(skill_path).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, int] = {
        "skill_md_lines": 0,
        "reference_count": 0,
        "total_lines": 0,
        "python_files_checked": 0,
    }

    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        errors.append("SKILL.md does not exist")
        return {"valid": False, "errors": errors, "warnings": warnings, "metrics": metrics}

    content = skill_md.read_text(encoding="utf-8")
    metrics["skill_md_lines"] = len(content.splitlines())
    metrics["total_lines"] += metrics["skill_md_lines"]
    frontmatter, body = parse_frontmatter(content)

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        name = frontmatter.get("name", "")
        if name != root.name:
            errors.append(f"frontmatter name '{name}' does not match directory '{root.name}'")
        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", name):
            errors.append(f"frontmatter name '{name}' is not a valid skill name")
        description = frontmatter.get("description", "")
        if not description:
            errors.append("frontmatter missing description")
        elif len(description) > 1024:
            errors.append(f"description exceeds 1024 characters ({len(description)})")

    if len(body.splitlines()) > 500:
        warnings.append("SKILL.md body exceeds 500 lines")

    for dirname in REQUIRED_DIRS:
        directory = root / dirname
        if not directory.is_dir():
            errors.append(f"missing required directory: {dirname}/")
        elif not any(directory.iterdir()):
            errors.append(f"empty directory without .gitkeep: {dirname}/")

    for rel_path in extract_file_references(content):
        if not (root / rel_path).exists():
            errors.append(f"referenced file does not exist: {rel_path}")

    references_dir = root / "references"
    if references_dir.is_dir():
        for path in references_dir.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            lines = len(text.splitlines())
            metrics["reference_count"] += 1
            metrics["total_lines"] += lines
            if lines > 1000:
                errors.append(f"reference file exceeds 1000 lines: {path.relative_to(root)}")
            elif lines > 300 and not has_toc(text):
                warnings.append(f"reference file >300 lines without TOC: {path.relative_to(root)}")
            for rel_path in extract_file_references(text):
                if not (root / rel_path).exists():
                    errors.append(
                        f"cross-reference in {path.relative_to(root)} does not exist: {rel_path}"
                    )

    evals_path = root / "evals" / "evals.json"
    if not evals_path.is_file():
        errors.append("evals/evals.json does not exist")
    else:
        try:
            evals = json.loads(evals_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is invalid JSON: {exc}")
        else:
            if evals.get("skill_name") != root.name:
                errors.append("evals/evals.json skill_name does not match directory name")
            if not isinstance(evals.get("evals"), list) or not evals["evals"]:
                errors.append("evals/evals.json must contain at least one eval")

    for path in (root / "scripts").glob("*.py"):
        metrics["python_files_checked"] += 1
        metrics["total_lines"] += count_lines(path)
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"python syntax error in {path.relative_to(root)}: {exc.msg}")

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

    result = validate_skill(sys.argv[1])
    root = Path(sys.argv[1]).resolve()
    status = "VALID" if result["valid"] else "INVALID"
    print(f"\nSkill: {root.name}")
    print(f"Status: {status}")
    print(f"SKILL.md lines: {result['metrics']['skill_md_lines']}")
    print(f"Reference files: {result['metrics']['reference_count']}")
    print(f"Python files checked: {result['metrics']['python_files_checked']}")
    print(f"Total lines: {result['metrics']['total_lines']}")

    if result["errors"]:
        print(f"\nErrors ({len(result['errors'])}):")
        for error in result["errors"]:
            print(f"  ERROR: {error}")

    if result["warnings"]:
        print(f"\nWarnings ({len(result['warnings'])}):")
        for warning in result["warnings"]:
            print(f"  WARN: {warning}")

    if result["valid"] and not result["warnings"]:
        print("\nNo issues found.")

    print("\n--- JSON ---")
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
