#!/usr/bin/env python3
"""Focused regressions for shared README, PNG, and description validators."""

from __future__ import annotations

import importlib.util
import struct
import sys
import tempfile
import unittest
import zlib
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast

from png_validation import PNG_SIGNATURE, parse_png


SCRIPT_DIR = Path(__file__).resolve().parent


class ReadmeValidator(Protocol):
    """Typed surface used from the hyphenated README validator script."""

    def validate_readme_catalog(self, readme: str, skill_names: list[str]) -> list[str]: ...


class ArtValidator(Protocol):
    """Typed surface used from the hyphenated artwork validator script."""

    def validate_png(self, path: Path, errors: list[str]) -> None: ...

    def validate_readme_art(
        self,
        readme: str,
        names: list[str],
        errors: list[str],
    ) -> None: ...


class DescriptionValidator(Protocol):
    """Typed surface used from the hyphenated description validator script."""

    MAX_DESCRIPTION_CHARS: int

    def collect(self, repo_root: Path) -> list[DescriptionRecord]: ...

    def description_budget_errors(
        self,
        repo_root: Path,
        descriptions: Sequence[DescriptionRecord],
    ) -> list[str]: ...

    def parse_description(self, path: Path) -> str: ...


class DescriptionRecord(Protocol):
    """Description field consumed by the repository budget calculation."""

    description: str


def load_script(filename: str, module_name: str) -> ModuleType:
    """Load one repository script whose filename is not importable as a module."""

    path = SCRIPT_DIR / filename
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


README_VALIDATOR = cast(
    ReadmeValidator,
    load_script("validate-readme-skills.py", "validate_readme_skills_regression"),
)
ART_VALIDATOR = cast(
    ArtValidator,
    load_script("validate-skill-art.py", "validate_skill_art_regression"),
)
DESCRIPTION_VALIDATOR = cast(
    DescriptionValidator,
    load_script(
        "check-skill-description-budget.py",
        "check_skill_description_budget_regression",
    ),
)


def readme_skill_section(skill_name: str) -> str:
    """Build the exact public catalog/card block required for one skill."""

    return (
        "## Available Skills\n\n"
        f"### `{skill_name}`\n\n"
        f"`npx skills add jpcaparas/skills --skill {skill_name}`\n\n"
        '<p align="center">\n'
        f'  <img src="skills/{skill_name}/skill-card.png" '
        f'alt="16-bit side-scrolling pixel art badge for {skill_name}" '
        'width="480">\n'
        "</p>\n\n"
    )


def readme_with_section(section: str) -> str:
    """Place a catalog section after the required visible global command."""

    return (
        "# Test skills\n\n"
        "`npx skills add jpcaparas/skills`\n\n"
        f"{section}"
    )


def png_chunk(chunk_type: bytes, payload: bytes, *, valid_crc: bool = True) -> bytes:
    """Build one PNG chunk, optionally retaining the historical bad CRC."""

    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF if valid_crc else 0
    return struct.pack(">I", len(payload)) + chunk_type + payload + struct.pack(">I", crc)


def rgb_png(width: int, height: int, compressed_scanlines: bytes) -> bytes:
    """Build a correctly framed RGB PNG around supplied compressed scanlines."""

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", compressed_scanlines)
        + png_chunk(b"IEND", b"")
    )


def indexed_png(
    *,
    palette: bytes,
    palette_after_idat: bool = False,
) -> bytes:
    """Build a 1-bit indexed PNG with configurable PLTE placement."""

    ihdr = struct.pack(">IIBBBBB", 1, 1, 1, 3, 0, 0, 0)
    image_data = png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
    palette_chunk = png_chunk(b"PLTE", palette)
    body = (
        image_data + palette_chunk
        if palette_after_idat
        else palette_chunk + image_data
    )
    return PNG_SIGNATURE + png_chunk(b"IHDR", ihdr) + body + png_chunk(b"IEND", b"")


class ReadmeCommentRegressionTests(unittest.TestCase):
    """Require catalog evidence to be visible rather than HTML-commented."""

    def test_visible_catalog_and_art_are_accepted(self) -> None:
        readme = readme_with_section(readme_skill_section("example"))

        catalog_errors = README_VALIDATOR.validate_readme_catalog(readme, ["example"])
        art_errors: list[str] = []
        ART_VALIDATOR.validate_readme_art(readme, ["example"], art_errors)

        self.assertEqual([], catalog_errors)
        self.assertEqual([], art_errors)

    def test_entire_commented_catalog_fails_both_validators(self) -> None:
        commented_section = f"<!--\n{readme_skill_section('example')}-->\n"
        readme = readme_with_section(commented_section)

        catalog_errors = README_VALIDATOR.validate_readme_catalog(readme, ["example"])
        art_errors: list[str] = []
        ART_VALIDATOR.validate_readme_art(readme, ["example"], art_errors)

        self.assertEqual(
            ["README.md is missing a '## Available Skills' section."],
            catalog_errors,
        )
        self.assertTrue(
            any("exactly 1 skill-card PNG images; found 0" in error for error in art_errors),
            art_errors,
        )

    def test_entire_fenced_catalog_fails_both_validators(self) -> None:
        fenced_section = f"```markdown\n{readme_skill_section('example')}```\n"
        readme = readme_with_section(fenced_section)

        catalog_errors = README_VALIDATOR.validate_readme_catalog(readme, ["example"])
        art_errors: list[str] = []
        ART_VALIDATOR.validate_readme_art(readme, ["example"], art_errors)

        self.assertEqual(
            ["README.md is missing a '## Available Skills' section."],
            catalog_errors,
        )
        self.assertTrue(
            any("exactly 1 skill-card PNG images; found 0" in error for error in art_errors),
            art_errors,
        )

    def test_commented_skill_header_is_not_catalog_evidence(self) -> None:
        visible_section = readme_skill_section("example")
        readme = readme_with_section(
            visible_section.replace(
                "### `example`",
                "<!-- ### `example` -->",
                1,
            )
        )

        catalog_errors = README_VALIDATOR.validate_readme_catalog(readme, ["example"])

        self.assertTrue(
            any("missing skill sections for: example" in error for error in catalog_errors),
            catalog_errors,
        )

    def test_commented_skill_card_is_not_art_evidence(self) -> None:
        visible_section = readme_skill_section("example")
        card = (
            '<p align="center">\n'
            '  <img src="skills/example/skill-card.png" '
            'alt="16-bit side-scrolling pixel art badge for example" '
            'width="480">\n'
            "</p>"
        )
        readme = readme_with_section(
            visible_section.replace(card, f"<!--\n{card}\n-->", 1)
        )
        art_errors: list[str] = []

        ART_VALIDATOR.validate_readme_art(readme, ["example"], art_errors)

        self.assertTrue(
            any("exactly 1 skill-card PNG images; found 0" in error for error in art_errors),
            art_errors,
        )

    def test_html_comment_literal_in_fence_does_not_hide_visible_catalog(self) -> None:
        fenced_example = "```markdown\n<!-- example opener\n```\n\n"
        readme = readme_with_section(
            fenced_example + readme_skill_section("example")
        )

        catalog_errors = README_VALIDATOR.validate_readme_catalog(readme, ["example"])
        art_errors: list[str] = []
        ART_VALIDATOR.validate_readme_art(readme, ["example"], art_errors)

        self.assertEqual([], catalog_errors)
        self.assertEqual([], art_errors)


class PngRegressionTests(unittest.TestCase):
    """Reject files that only imitate PNG signatures, fields, and chunk names."""

    def test_accepts_a_decodable_png_with_valid_chunks_and_crc(self) -> None:
        scanline = b"\x00\x11\x22\x33"
        png = rgb_png(1, 1, zlib.compress(scanline))

        metadata = parse_png(png)

        self.assertIsNotNone(metadata)

    def test_rejects_the_old_fake_header_false_positive(self) -> None:
        ihdr = struct.pack(">IIBBBBB", 1024, 576, 8, 2, 0, 0, 0)
        fake = (
            PNG_SIGNATURE
            + png_chunk(b"IHDR", ihdr, valid_crc=False)
            + png_chunk(b"IDAT", b"", valid_crc=False)
            + png_chunk(b"IEND", b"", valid_crc=False)
        ).ljust(10_000, b"\x00")

        with tempfile.TemporaryDirectory(prefix="shared-validator-png-") as temp_dir:
            path = Path(temp_dir) / "skill-card.png"
            path.write_bytes(fake)
            errors: list[str] = []

            ART_VALIDATOR.validate_png(path, errors)

        self.assertTrue(any("must be a valid PNG raster image" in error for error in errors))

    def test_rejects_valid_chunk_labels_without_decodable_image_data(self) -> None:
        fake = rgb_png(1, 1, b"not a zlib stream")

        with self.assertRaisesRegex(ValueError, "IDAT data is not a valid zlib stream"):
            parse_png(fake)

    def test_rejects_crc_mismatch_on_otherwise_decodable_png(self) -> None:
        ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
        fake = (
            PNG_SIGNATURE
            + png_chunk(b"IHDR", ihdr, valid_crc=False)
            + png_chunk(b"IDAT", zlib.compress(b"\x00\x11\x22\x33"))
            + png_chunk(b"IEND", b"")
        )

        with self.assertRaisesRegex(ValueError, "IHDR chunk CRC does not match"):
            parse_png(fake)

    def test_accepts_valid_indexed_palette_before_image_data(self) -> None:
        metadata = parse_png(indexed_png(palette=b"\x00\x00\x00\xff\xff\xff"))

        self.assertIn("PLTE", metadata.chunks)

    def test_rejects_palette_after_image_data(self) -> None:
        fake = indexed_png(
            palette=b"\x00\x00\x00\xff\xff\xff",
            palette_after_idat=True,
        )

        with self.assertRaisesRegex(ValueError, "PLTE must appear before the first IDAT"):
            parse_png(fake)

    def test_rejects_malformed_palette_shape(self) -> None:
        fake = indexed_png(palette=b"\x00\x00\x00\xff")

        with self.assertRaisesRegex(ValueError, "PLTE must contain between 1 and 256"):
            parse_png(fake)

    def test_bounds_decompression_to_declared_raster_size(self) -> None:
        oversized_scanline = zlib.compress(b"\x00" * 1_000_000)
        fake = rgb_png(1, 1, oversized_scanline)

        with self.assertRaisesRegex(ValueError, "expands beyond the declared image dimensions"):
            parse_png(fake)

    def test_rejects_truncated_stream_after_expected_pixels_are_emitted(self) -> None:
        complete_stream = zlib.compress(b"\x00\x11\x22\x33")
        fake = rgb_png(1, 1, complete_stream[:-1])

        with self.assertRaisesRegex(ValueError, "IDAT zlib stream is incomplete"):
            parse_png(fake)


class DescriptionBudgetRegressionTests(unittest.TestCase):
    """Count YAML scalar values after anchors and aliases are resolved."""

    def test_yaml_alias_is_resolved_before_budget_counting(self) -> None:
        resolved_description = "x" * (DESCRIPTION_VALIDATOR.MAX_DESCRIPTION_CHARS + 1)
        skill_markdown = (
            "---\n"
            f"shared_description: &shared '{resolved_description}'\n"
            "description: *shared\n"
            "---\n\n"
            "# Example\n"
        )

        with tempfile.TemporaryDirectory(prefix="shared-validator-yaml-") as temp_dir:
            repo_root = Path(temp_dir)
            skill_dir = repo_root / "skills" / "example"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(skill_markdown, encoding="utf-8")

            descriptions = DESCRIPTION_VALIDATOR.collect(repo_root)
            errors = DESCRIPTION_VALIDATOR.description_budget_errors(
                repo_root,
                descriptions,
            )

        self.assertEqual(1, len(descriptions))
        self.assertEqual(resolved_description, descriptions[0].description)
        self.assertTrue(any("451 chars > 450" in error for error in errors), errors)

    def test_rejects_duplicate_description_keys(self) -> None:
        skill_markdown = (
            "---\n"
            "description: first value\n"
            "description: second value\n"
            "---\n"
        )

        self.assert_description_error(skill_markdown, "duplicate key 'description'")

    def test_resolves_folded_and_literal_description_scalars(self) -> None:
        cases = {
            "folded": (
                "---\ndescription: >-\n  first line\n  second line\n---\n",
                "first line second line",
            ),
            "literal": (
                "---\ndescription: |-\n  first line\n  second line\n---\n",
                "first line\nsecond line",
            ),
            "quoted empty": ("---\ndescription: \"\"\n---\n", ""),
        }

        for name, (skill_markdown, expected) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(expected, self.parse_description(skill_markdown))

    def test_rejects_empty_untyped_description_scalar(self) -> None:
        self.assert_description_error(
            "---\ndescription:\n---\n",
            "description must resolve to a string",
        )

    def test_rejects_malformed_yaml(self) -> None:
        self.assert_description_error(
            "---\ndescription: [unterminated\n---\n",
            "invalid YAML frontmatter",
        )

    def test_rejects_non_string_description(self) -> None:
        self.assert_description_error(
            "---\ndescription:\n  - list item\n---\n",
            "description must resolve to a string",
        )

    def test_rejects_symlinked_skill_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="shared-validator-description-"
        ) as temp_dir:
            repo_root = Path(temp_dir)
            skill_dir = repo_root / "skills" / "example"
            skill_dir.mkdir(parents=True)
            outside = repo_root / "outside.md"
            outside.write_text("---\ndescription: external\n---\n", encoding="utf-8")
            (skill_dir / "SKILL.md").symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "must be a regular file"):
                DESCRIPTION_VALIDATOR.collect(repo_root)

    def parse_description(self, content: str) -> str:
        """Parse one isolated SKILL.md fixture."""

        with tempfile.TemporaryDirectory(
            prefix="shared-validator-description-"
        ) as temp_dir:
            path = Path(temp_dir) / "SKILL.md"
            path.write_text(content, encoding="utf-8")
            return DESCRIPTION_VALIDATOR.parse_description(path)

    def assert_description_error(self, content: str, message: str) -> None:
        """Require one isolated SKILL.md fixture to fail with a useful reason."""

        with tempfile.TemporaryDirectory(
            prefix="shared-validator-description-"
        ) as temp_dir:
            path = Path(temp_dir) / "SKILL.md"
            path.write_text(content, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, message):
                DESCRIPTION_VALIDATOR.parse_description(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
