#!/usr/bin/env python3
"""Validate README skill-card raster artwork and prompt harness files."""

from __future__ import annotations

import importlib.util
import re
import struct
import sys
from pathlib import Path


CARD_FILENAME = "skill-card.png"
PROMPT_FILENAME = "skill-card.prompt.md"
CARD_WIDTH = "480"
FINAL_WIDTH = 1024
FINAL_HEIGHT = 576
MAX_CARD_BYTES = 750_000
ALLOWED_PNG_CHUNKS = {"IHDR", "IDAT", "IEND"}
NO_TEXT_RULE = (
    "No visible text, no letters, no numbers, no typography, no captions, "
    "no labels, no logos, no watermarks, no pseudo-text, no glyph-like marks, "
    "no UI copy, no code characters, no punctuation, no checkmarks, no question marks."
)


def load_renderer(repo_root: Path):
    script_path = repo_root / "scripts" / "render-skill-art.py"
    spec = importlib.util.spec_from_file_location("render_skill_art", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fail(errors: list[str]) -> int:
    print("README skill art validation failed:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    return 2


def skill_names(skills_root: Path) -> list[str]:
    return sorted(path.parent.name for path in skills_root.glob("*/SKILL.md") if path.is_file())


def png_chunks(path: Path) -> tuple[int, int, list[str]] | None:
    data = path.read_bytes()
    if len(data) < 24 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    if data[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", data[16:24])
    chunks: list[str] = []
    offset = 8
    while offset + 8 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_type = data[offset + 4 : offset + 8].decode("latin1")
        chunks.append(chunk_type)
        offset += 12 + length
        if chunk_type == "IEND":
            break
    return width, height, chunks


def validate_png(path: Path, errors: list[str]) -> None:
    parsed = png_chunks(path)
    if parsed is None:
        errors.append(f"{path} must be a PNG raster image.")
        return

    width, height, chunks = parsed
    if width != FINAL_WIDTH or height != FINAL_HEIGHT:
        errors.append(f"{path} must be normalized to {FINAL_WIDTH}x{FINAL_HEIGHT}; found {width}x{height}.")

    extra_chunks = sorted(set(chunks) - ALLOWED_PNG_CHUNKS)
    if extra_chunks:
        errors.append(f"{path} must be stripped PNG with only IHDR/IDAT/IEND chunks; found {extra_chunks}.")

    size = path.stat().st_size
    if size < 10_000:
        errors.append(f"{path} is suspiciously small for a generated raster badge.")
    if size > MAX_CARD_BYTES:
        errors.append(f"{path} is too large for README use; run `python3 scripts/render-skill-art.py --force`.")


def validate_prompt(path: Path, skill_name: str, expected_prompt: str, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"Missing prompt harness file: skills/{skill_name}/{PROMPT_FILENAME}")
        return

    prompt = path.read_text(encoding="utf-8")
    if prompt != expected_prompt:
        errors.append(
            f"{path} has drifted from scripts/render-skill-art.py; "
            "run `python3 scripts/render-skill-art.py --prompts-only`."
        )

    required_fragments = [
        "Nano Banana 2 image generation prompt",
        "Aspect ratio: 16:9.",
        "side-scrolling 16-bit pixel game art",
        "rectangular raster badge",
        NO_TEXT_RULE,
        skill_name,
    ]
    for fragment in required_fragments:
        if fragment not in prompt:
            errors.append(f"{path} must include prompt constraint: {fragment}")


def validate_readme_art(readme: str, names: list[str], errors: list[str]) -> None:
    img_count = len(re.findall(r"<img\s+src=\"skills/[^/]+/skill-card\.png\"", readme))
    if img_count != len(names):
        errors.append(
            f"README.md must contain exactly {len(names)} skill-card PNG images; found {img_count}."
        )

    if "skill-card.svg" in readme:
        errors.append("README.md must use generated raster PNG cards, not SVG cards.")

    old_placement = re.findall(
        r"<p align=\"center\">\n"
        r"  <img src=\"skills/([^/]+)/skill-card\.png\"[^>]*>\n"
        r"</p>\n\n"
        r"### `([^`]+)`",
        readme,
    )
    if old_placement:
        misplaced = sorted({name for name, heading in old_placement if name == heading})
        errors.append(
            "README.md must place each skill-card PNG after the install command, not above "
            f"the section heading. Old-placement sections: {', '.join(misplaced)}"
        )

    for name in names:
        expected = (
            f"### `{name}`\n\n"
            f"`npx skills add jpcaparas/skills --skill {name}`\n\n"
            f'<p align="center">\n'
            f'  <img src="skills/{name}/{CARD_FILENAME}" '
            f'alt="16-bit side-scrolling pixel art badge for {name}" '
            f'width="{CARD_WIDTH}">\n'
            f'</p>\n\n'
        )
        if expected not in readme:
            errors.append(
                "README.md must place the constrained PNG skill card immediately "
                f"after the install command for `{name}` with path "
                f"skills/{name}/{CARD_FILENAME}."
            )


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    readme_path = repo_root / "README.md"
    skills_root = repo_root / "skills"
    renderer = load_renderer(repo_root)

    names = skill_names(skills_root)
    readme = readme_path.read_text(encoding="utf-8")
    errors: list[str] = []

    validate_readme_art(readme, names, errors)

    for name in names:
        skill_dir = skills_root / name
        card_path = skill_dir / CARD_FILENAME
        if not card_path.is_file():
            errors.append(f"Missing skill art file: skills/{name}/{CARD_FILENAME}")
        else:
            validate_png(card_path, errors)
        validate_prompt(skill_dir / PROMPT_FILENAME, name, renderer.prompt_for_skill(name), errors)

    svg_cards = sorted(skills_root.glob("*/skill-card.svg"))
    for path in svg_cards:
        errors.append(f"Remove SVG skill art file; generated raster is required: {path}")

    if errors:
        return fail(errors)

    print(
        "README.md includes constrained Nano Banana PNG skill art cards for "
        f"all {len(names)} skills."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
