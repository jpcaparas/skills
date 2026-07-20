#!/usr/bin/env python3
"""Check startup-visible skill descriptions stay within a compact budget."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

from yaml_validation import load_unique_yaml


MAX_DESCRIPTION_CHARS = 450
MAX_TOTAL_DESCRIPTION_CHARS = 12_500


@dataclass(frozen=True)
class SkillDescription:
    name: str
    path: Path
    description: str


def parse_description(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing YAML frontmatter")

    closing_index = next(
        (index for index, line in enumerate(lines[1:], start=1) if line == "---"),
        None,
    )
    if closing_index is None:
        raise ValueError("frontmatter is not closed")

    frontmatter = "\n".join(lines[1:closing_index])
    try:
        parsed = load_unique_yaml(frontmatter)
    except (yaml.YAMLError, RecursionError) as exc:
        raise ValueError(f"invalid YAML frontmatter: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("YAML frontmatter must be a mapping")

    if "description" not in parsed:
        raise ValueError("missing description")
    description: object = parsed.get("description")
    if isinstance(description, str):
        return description
    raise ValueError("description must resolve to a string")


def collect(repo_root: Path) -> list[SkillDescription]:
    skills_root = repo_root / "skills"
    descriptions: list[SkillDescription] = []
    for skill_md in sorted(skills_root.glob("*/SKILL.md")):
        if skill_md.is_symlink():
            raise ValueError(
                f"{skill_md.relative_to(repo_root)} must be a regular file, not a symlink"
            )
        descriptions.append(
            SkillDescription(
                name=skill_md.parent.name,
                path=skill_md,
                description=parse_description(skill_md),
            )
        )
    return descriptions


def description_budget_errors(
    repo_root: Path,
    descriptions: Sequence[SkillDescription],
) -> list[str]:
    """Return individual and aggregate errors for resolved descriptions."""

    errors: list[str] = []
    total_chars = sum(len(item.description) for item in descriptions)
    if total_chars > MAX_TOTAL_DESCRIPTION_CHARS:
        errors.append(
            "total frontmatter description budget exceeded: "
            f"{total_chars} chars > {MAX_TOTAL_DESCRIPTION_CHARS}"
        )

    for item in descriptions:
        if len(item.description) > MAX_DESCRIPTION_CHARS:
            errors.append(
                f"{item.path.relative_to(repo_root)} description is "
                f"{len(item.description)} chars > {MAX_DESCRIPTION_CHARS}"
            )
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    try:
        descriptions = collect(repo_root)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = description_budget_errors(repo_root, descriptions)
    total_chars = sum(len(item.description) for item in descriptions)

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
        f"max {max((len(item.description) for item in descriptions), default=0)} chars."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
