#!/usr/bin/env python3
"""Canonical inventory of skills/<category>/<name> packages, not their fixtures.

Categories organise source files; the globally unique leaf name is still the
installer/invocation identity. Never recurse into a package: several skills ship
deliberately invalid SKILL.md fixtures that must not become installable entries.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from yaml_validation import load_unique_yaml


CATEGORIES = (
    "engineering",
    "testing",
    "agents",
    "writing",
    "research",
    "creative",
    "productivity",
    "fun",
)
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


@dataclass(frozen=True)
class Skill:
    name: str
    category: str
    directory: Path

    @property
    def repo_path(self) -> str:
        return f"skills/{self.category}/{self.name}"


def discover_skills(skills_root: Path) -> list[Skill]:
    """Return the complete sorted inventory or fail without a partial result."""
    if skills_root.is_symlink() or not skills_root.is_dir():
        raise ValueError(f"Skills root must be a real directory: {skills_root}")
    if (skills_root / "SKILL.md").exists() or (skills_root / "SKILL.md").is_symlink():
        raise ValueError(f"Container SKILL.md would hide nested skills: {skills_root}")

    skills: list[Skill] = []
    seen: dict[str, Path] = {}
    for category in sorted(skills_root.iterdir()):
        if category.is_symlink():
            raise ValueError(f"Category must not be a symlink: {category}")
        if not category.is_dir():
            continue
        if category.name not in CATEGORIES:
            raise ValueError(f"Unknown category or unnamespaced skill: {category}")
        if (category / "SKILL.md").exists() or (category / "SKILL.md").is_symlink():
            raise ValueError(f"Container SKILL.md would hide nested skills: {category}")

        category_skills: list[Skill] = []
        for directory in sorted(category.iterdir()):
            if directory.is_symlink():
                raise ValueError(f"Skill directory must not be a symlink: {directory}")
            if not directory.is_dir():
                continue
            if len(directory.name) > 64 or SLUG.fullmatch(directory.name) is None:
                raise ValueError(f"Invalid skill directory name: {directory}")
            entrypoint = directory / "SKILL.md"
            if entrypoint.is_symlink():
                raise ValueError(
                    f"installable SKILL.md must not be a symlink; must be a regular file: {entrypoint}"
                )
            if not entrypoint.is_file():
                raise ValueError(
                    f"Missing regular SKILL.md in skill directory: {directory}"
                )
            lines = entrypoint.read_text(encoding="utf-8").splitlines()
            if not lines or lines[0] != "---" or "---" not in lines[1:]:
                raise ValueError(f"Missing or unclosed YAML frontmatter: {entrypoint}")
            try:
                metadata = load_unique_yaml("\n".join(lines[1 : lines.index("---", 1)]))
            except (yaml.YAMLError, RecursionError) as exc:
                raise ValueError(
                    f"Invalid YAML frontmatter in {entrypoint}: {exc}"
                ) from exc
            if not isinstance(metadata, dict) or metadata.get("name") != directory.name:
                raise ValueError(
                    f"Frontmatter name must match directory '{directory.name}': {entrypoint}"
                )
            if directory.name in seen:
                raise ValueError(
                    f"Duplicate skill name '{directory.name}': {seen[directory.name]} and {directory}"
                )
            seen[directory.name] = directory
            category_skills.append(Skill(directory.name, category.name, directory))
        if not category_skills:
            raise ValueError(f"Empty skill category: {category}")
        skills.extend(category_skills)
    if not skills:
        raise ValueError(f"No installable skills found under {skills_root}")
    return sorted(
        skills, key=lambda skill: (CATEGORIES.index(skill.category), skill.name)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skills-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "skills",
    )
    parser.add_argument(
        "--names",
        action="store_true",
        help="Print stable install names instead of directory paths.",
    )
    args = parser.parse_args()
    try:
        skills = discover_skills(args.skills_root)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for value in sorted(
        skill.name if args.names else str(skill.directory) for skill in skills
    ):
        print(value)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
