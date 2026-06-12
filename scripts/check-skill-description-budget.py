#!/usr/bin/env python3
"""Check startup-visible skill descriptions stay within a compact budget."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


MAX_DESCRIPTION_CHARS = 450
MAX_TOTAL_DESCRIPTION_CHARS = 12_000


@dataclass(frozen=True)
class SkillDescription:
    name: str
    path: Path
    description: str


def parse_description(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("missing YAML frontmatter")
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError("frontmatter is not closed")

    frontmatter = text[3:end]
    match = re.search(r'^description:\s*"(.*)"\s*$', frontmatter, re.MULTILINE)
    if match:
        return match.group(1)

    match = re.search(r"^description:\s*(.+?)\s*$", frontmatter, re.MULTILINE)
    if match:
        return match.group(1).strip("'\"")

    raise ValueError("missing description")


def collect(repo_root: Path) -> list[SkillDescription]:
    skills_root = repo_root / "skills"
    descriptions: list[SkillDescription] = []
    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        descriptions.append(
            SkillDescription(
                name=skill_md.parent.name,
                path=skill_md,
                description=parse_description(skill_md),
            )
        )
    return descriptions


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    errors: list[str] = []

    try:
        descriptions = collect(repo_root)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    total_chars = sum(len(item.description) for item in descriptions)
    too_long = [
        item
        for item in descriptions
        if len(item.description) > MAX_DESCRIPTION_CHARS
    ]

    if total_chars > MAX_TOTAL_DESCRIPTION_CHARS:
        errors.append(
            "total frontmatter description budget exceeded: "
            f"{total_chars} chars > {MAX_TOTAL_DESCRIPTION_CHARS}"
        )

    for item in too_long:
        errors.append(
            f"{item.path.relative_to(repo_root)} description is "
            f"{len(item.description)} chars > {MAX_DESCRIPTION_CHARS}"
        )

    if errors:
        print("Skill description budget check failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print(
            "\nKeep startup-visible frontmatter concise. Move detailed trigger "
            "rules into the SKILL.md body or references.",
            file=sys.stderr,
        )
        return 1

    print(
        "Skill descriptions fit startup budget: "
        f"{len(descriptions)} skills, {total_chars} chars total, "
        f"max {max(len(item.description) for item in descriptions)} chars."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
