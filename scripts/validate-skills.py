#!/usr/bin/env python3
"""Check what every skill package must get right to install and load.

Each check guards a failure that an installer, a host, or an agent would hit at
runtime. How a skill words, orders, or sizes its instructions is the author's
decision and is deliberately not checked here.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import unquote

from readme_markdown import markdown_visible_text
from skill_catalog import Skill, discover_skills, read_frontmatter

# Hosts put every description in context at startup. Codex shortens them, then
# drops whole skills, once the list passes about 2% of its context window.
MAX_DESCRIPTION_CHARS = 450
MAX_TOTAL_DESCRIPTION_CHARS = 13_000

ENTRYPOINT = "SKILL.md"
# Fixtures under evals/ are test data and may be deliberately broken.
FIXTURE_DIRECTORY = "evals"

INLINE_CODE = re.compile(r"`[^`\n]*`")
MARKDOWN_LINK = re.compile(r"\]\(\s*<?([^)\s>]+)")
NOT_A_PACKAGE_PATH = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|#|/|~|\{|<)", re.IGNORECASE)


def read_description(entrypoint: Path) -> str:
    """Return the resolved description, as hosts see it after YAML parsing."""
    description = read_frontmatter(entrypoint).get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"description must be a non-empty string: {entrypoint}")
    return description


def description_budget_errors(descriptions: Mapping[str, str]) -> list[str]:
    errors = [
        f"{name}: description is {len(text)} characters; the limit is {MAX_DESCRIPTION_CHARS}."
        for name, text in descriptions.items()
        if len(text) > MAX_DESCRIPTION_CHARS
    ]
    total = sum(len(text) for text in descriptions.values())
    if total > MAX_TOTAL_DESCRIPTION_CHARS:
        errors.append(
            f"All descriptions total {total} characters; the limit is "
            f"{MAX_TOTAL_DESCRIPTION_CHARS}. Shorten descriptions before adding more skills."
        )
    return errors


def nested_entrypoint_errors(skill: Skill) -> list[str]:
    """Some hosts install any file named SKILL.md, including eval fixtures."""
    return [
        f"{skill.repo_path}: rename {nested.relative_to(skill.directory)}; hosts "
        f"install every file named {ENTRYPOINT} as a skill (use SKILL.fixture.md)."
        for nested in sorted(skill.directory.rglob(ENTRYPOINT))
        if nested.parent != skill.directory
    ]


def broken_link_errors(skill: Skill) -> list[str]:
    """Installed packages are standalone, so SKILL.md links must stay inside."""
    package = skill.directory.resolve()
    visible = markdown_visible_text(
        (skill.directory / ENTRYPOINT).read_text(encoding="utf-8")
    )
    errors: list[str] = []
    for target in MARKDOWN_LINK.findall(INLINE_CODE.sub("", visible)):
        if NOT_A_PACKAGE_PATH.match(target):
            continue
        relative = unquote(target.split("#", 1)[0].split("?", 1)[0])
        resolved = (package / relative).resolve()
        if not resolved.is_relative_to(package):
            errors.append(
                f"{skill.repo_path}/{ENTRYPOINT}: link leaves the package and "
                f"breaks once the skill is installed: {target}"
            )
        elif not resolved.exists():
            errors.append(
                f"{skill.repo_path}/{ENTRYPOINT}: linked file does not exist: {target}"
            )
    return errors


def python_syntax_errors(skill: Skill) -> list[str]:
    errors: list[str] = []
    for script in sorted(skill.directory.rglob("*.py")):
        relative = script.relative_to(skill.directory)
        if relative.parts[0] == FIXTURE_DIRECTORY:
            continue
        try:
            compile(script.read_text(encoding="utf-8"), str(script), "exec")
        except (SyntaxError, ValueError) as exc:
            errors.append(f"{skill.repo_path}/{relative}: does not compile: {exc}")
    return errors


def validate(skills_root: Path) -> list[str]:
    skills = discover_skills(skills_root)
    errors: list[str] = []
    descriptions: dict[str, str] = {}
    for skill in skills:
        try:
            descriptions[skill.name] = read_description(skill.directory / ENTRYPOINT)
        except ValueError as exc:
            errors.append(str(exc))
        errors += nested_entrypoint_errors(skill)
        errors += broken_link_errors(skill)
        errors += python_syntax_errors(skill)
    return errors + description_budget_errors(descriptions)


def main() -> int:
    skills_root = Path(__file__).resolve().parents[1] / "skills"
    try:
        errors = validate(skills_root)
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
    if errors:
        print("Skill package validation failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print("Every skill package installs cleanly and fits the description budget.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
