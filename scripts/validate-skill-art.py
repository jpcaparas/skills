#!/usr/bin/env python3
"""Check that every skill has a README-ready card and that README.md shows it."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from readme_markdown import markdown_visible_text
from skill_catalog import Skill, discover_skills


CARD_FILENAME = "skill-card.png"
CARD_WIDTH = "480"
CARD_SIZE = (1024, 576)
MAX_CARD_BYTES = 750_000
RENDER_HINT = "run `python3 scripts/render-skill-art.py --normalize-only`"


def validate_png(path: Path, errors: list[str]) -> None:
    if path.stat().st_size > MAX_CARD_BYTES:
        errors.append(
            f"{path} is larger than {MAX_CARD_BYTES} bytes; {RENDER_HINT}."
        )
        return

    try:
        with Image.open(path) as image:
            image_format, size, metadata = image.format, image.size, dict(image.info)
            # Decode every pixel: a valid header on truncated data still opens.
            image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as exc:
        errors.append(f"{path} must be a decodable PNG image: {exc}.")
        return

    if image_format != "PNG":
        errors.append(f"{path} must be a PNG image; found {image_format}.")
        return
    if size != CARD_SIZE:
        errors.append(
            f"{path} must be {CARD_SIZE[0]}x{CARD_SIZE[1]}; found {size[0]}x{size[1]}."
        )
    if metadata:
        errors.append(
            f"{path} carries metadata ({', '.join(sorted(metadata))}); {RENDER_HINT}."
        )


def validate_readme_art(readme: str, skills: list[Skill], errors: list[str]) -> None:
    visible_readme = markdown_visible_text(readme)
    image_count = len(
        re.findall(r"<img\s+src=\"skills/[^\"]+/skill-card\.png\"", visible_readme)
    )
    if image_count != len(skills):
        errors.append(
            f"README.md must contain exactly {len(skills)} skill-card PNG images; "
            f"found {image_count}."
        )

    for skill in skills:
        expected = (
            f"#### `{skill.name}`\n\n"
            f"`npx skills add jpcaparas/skills --skill {skill.name}`\n\n"
            f'<p align="center">\n'
            f'  <img src="{skill.repo_path}/{CARD_FILENAME}" '
            f'alt="16-bit side-scrolling pixel art badge for {skill.name}" '
            f'width="{CARD_WIDTH}">\n'
            f"</p>\n\n"
        )
        if expected not in visible_readme:
            errors.append(
                "README.md must place the skill card immediately after the install "
                f"command for `{skill.name}` with path {skill.repo_path}/{CARD_FILENAME}; "
                "run `python3 scripts/render-skill-art.py --readme-only`."
            )


def fail(errors: list[str]) -> int:
    print("README skill art validation failed:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    return 1


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    try:
        skills = discover_skills(repo_root / "skills")
        readme = (repo_root / "README.md").read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        return fail([str(exc)])

    errors: list[str] = []
    validate_readme_art(readme, skills, errors)
    for skill in skills:
        card_path = skill.directory / CARD_FILENAME
        if card_path.is_file():
            validate_png(card_path, errors)
        else:
            errors.append(f"Missing skill card: {skill.repo_path}/{CARD_FILENAME}")
    if errors:
        return fail(errors)

    print(f"README.md shows a valid skill card for all {len(skills)} skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
