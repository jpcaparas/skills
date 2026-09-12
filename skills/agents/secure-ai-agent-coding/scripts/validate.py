#!/usr/bin/env python3
"""Validate the secure-ai-agent-coding skill package."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path


REQUIRED_DIRS = ["references", "scripts", "templates", "evals", "assets", "agents"]
REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "references/review-workflow.md",
    "references/controls.md",
    "references/implementation-patterns.md",
    "references/threat-model.md",
    "references/governance.md",
    "references/gotchas.md",
    "references/source-policy.md",
    "scripts/scan_patterns.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "templates/security-review.md",
    "evals/evals.json",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(content: str) -> dict[str, str]:
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---", 4)
    if end == -1:
        return {}
    frontmatter = content[4:end]
    parsed: dict[str, str] = {}
    for line in frontmatter.splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if match:
            value = match.group(2).strip()
            if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
                value = value[1:-1]
            parsed[match.group(1)] = value
    return parsed


def strip_code_fences(content: str) -> str:
    return re.sub(r"```[\s\S]*?```", "", content)


def extract_references(content: str) -> set[str]:
    refs: set[str] = set()
    stripped = strip_code_fences(content)
    pattern = re.compile(r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`")
    placeholder = re.compile(r"[{}<>]|\s")
    for match in pattern.finditer(stripped):
        ref = match.group(1)
        if not placeholder.search(ref):
            refs.add(ref)
    link_pattern = re.compile(r"\[[^\]]+\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)")
    for match in link_pattern.finditer(stripped):
        ref = match.group(1)
        if not placeholder.search(ref):
            refs.add(ref)
    return refs


def line_count(path: Path) -> int:
    return len(read_text(path).splitlines())


def validate(root: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    if not root.exists() or not root.is_dir():
        return {"valid": False, "errors": [f"not a directory: {root}"], "warnings": [], "metrics": metrics}

    for directory in REQUIRED_DIRS:
        if not (root / directory).is_dir():
            errors.append(f"missing directory: {directory}/")

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing file: {relative}")

    skill_md = root / "SKILL.md"
    if skill_md.is_file():
        content = read_text(skill_md)
        metrics["skill_md_lines"] = len(content.splitlines())
        metrics["total_lines"] += metrics["skill_md_lines"]
        frontmatter = parse_frontmatter(content)
        if frontmatter.get("name") != root.name:
            errors.append("frontmatter name must match directory name")
        description = frontmatter.get("description", "")
        if not description:
            errors.append("frontmatter description is required")
        elif len(description) > 1024:
            errors.append("frontmatter description exceeds 1024 characters")
        if metrics["skill_md_lines"] > 500:
            warnings.append("SKILL.md exceeds 500 lines")

        for ref in extract_references(content):
            if not (root / ref).exists():
                errors.append(f"SKILL.md reference does not exist: {ref}")

    refs_dir = root / "references"
    if refs_dir.is_dir():
        for path in refs_dir.rglob("*.md"):
            metrics["reference_count"] += 1
            count = line_count(path)
            metrics["total_lines"] += count
            if count > 1000:
                errors.append(f"reference file exceeds 1000 lines: {path.relative_to(root)}")
            for ref in extract_references(read_text(path)):
                if not (root / ref).exists():
                    errors.append(f"{path.relative_to(root)} reference does not exist: {ref}")

    evals = root / "evals" / "evals.json"
    if evals.is_file():
        try:
            data = json.loads(read_text(evals))
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is invalid JSON: {exc}")
        else:
            if data.get("skill_name") != root.name:
                errors.append("evals/evals.json skill_name must match directory name")
            if not isinstance(data.get("evals"), list) or not data["evals"]:
                errors.append("evals/evals.json must contain at least one eval")

    metadata = root / "metadata.json"
    if metadata.is_file():
        try:
            json.loads(read_text(metadata))
        except json.JSONDecodeError as exc:
            errors.append(f"metadata.json is invalid JSON: {exc}")

    return {"valid": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: python3 scripts/validate.py <skill-path>", file=sys.stderr)
        return 1

    root = Path(argv[0]).expanduser().resolve()
    result = validate(root)
    status = "VALID" if result["valid"] else "INVALID"
    metrics = result["metrics"]
    print(f"Skill: {root.name}")
    print(f"Status: {status}")
    print(f"SKILL.md lines: {metrics['skill_md_lines']}")
    print(f"Reference files: {metrics['reference_count']}")
    print(f"Total lines: {metrics['total_lines']}")

    for error in result["errors"]:
        print(f"ERROR: {error}")
    for warning in result["warnings"]:
        print(f"WARN: {warning}")

    print("--- JSON ---")
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
