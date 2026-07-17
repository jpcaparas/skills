#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

from readme_markdown import markdown_visible_text


REPO_SLUG = "jpcaparas/skills"
GLOBAL_INSTALL_COMMAND = f"npx skills add {REPO_SLUG}"


def fail(errors: list[str]) -> int:
    print("README skill validation failed:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    return 1


def validate_readme_catalog(readme: str, skill_names: list[str]) -> list[str]:
    """Return catalog errors for the README content visible to readers."""

    visible_readme = markdown_visible_text(readme)
    errors: list[str] = []

    available_match = re.search(
        r"^## Available Skills\s*$\n(?P<body>.*?)(?=^## |\Z)",
        visible_readme,
        re.MULTILINE | re.DOTALL,
    )
    if not available_match:
        return ["README.md is missing a '## Available Skills' section."]

    before_available = visible_readme[: available_match.start()]
    if GLOBAL_INSTALL_COMMAND not in before_available:
        errors.append(
            "README.md must document the global install command "
            f"`{GLOBAL_INSTALL_COMMAND}` before '## Available Skills'."
        )

    available_body = available_match.group("body")
    section_pattern = re.compile(
        r"^### `(?P<name>[^`]+)`\s*$\n(?P<body>.*?)(?=^### `|^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )

    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for match in section_pattern.finditer(available_body):
        name = match.group("name")
        body = match.group("body")
        if name in seen:
            duplicates.append(name)
        else:
            seen[name] = body

    if duplicates:
        errors.append(
            "README.md has duplicate skill headers in '## Available Skills': "
            + ", ".join(sorted(duplicates))
        )

    missing_sections = [name for name in skill_names if name not in seen]
    if missing_sections:
        errors.append(
            "README.md is missing skill sections for: " + ", ".join(missing_sections)
        )

    extra_sections = [name for name in seen if name not in skill_names]
    if extra_sections:
        errors.append(
            "README.md has skill sections without matching directories: "
            + ", ".join(sorted(extra_sections))
        )

    for skill_name in skill_names:
        if skill_name not in seen:
            continue

        expected_command = f"`npx skills add {REPO_SLUG} --skill {skill_name}`"
        lines = [line.strip() for line in seen[skill_name].splitlines()]
        first_nonempty = next((line for line in lines if line), "")
        if first_nonempty != expected_command:
            errors.append(
                f"Section '{skill_name}' must put {expected_command} on the first "
                "non-empty line after the header."
            )

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    readme_path = repo_root / "README.md"
    skills_root = repo_root / "skills"

    readme = readme_path.read_text(encoding="utf-8")
    skill_names = sorted(
        path.parent.name
        for path in skills_root.glob("*/SKILL.md")
        if path.is_file() and not path.is_symlink()
    )
    errors = validate_readme_catalog(readme, skill_names)
    symlinked_skill_files = sorted(
        path.relative_to(repo_root)
        for path in skills_root.glob("*/SKILL.md")
        if path.is_symlink()
    )
    errors.extend(
        f"Installable SKILL.md must not be a symlink: {path}"
        for path in symlinked_skill_files
    )

    if errors:
        return fail(errors)

    print(
        "README.md references all "
        f"{len(skill_names)} skills and includes the expected install commands."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
