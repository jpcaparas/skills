#!/usr/bin/env python3
"""Regressions for the shared README, skill-card, and skill-package validators."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast

from PIL import Image
from PIL.PngImagePlugin import PngInfo

from skill_catalog import Skill


SCRIPT_DIR = Path(__file__).resolve().parent
EXAMPLE = Skill("example", "engineering", Path("skills/engineering/example"))
CARD_SIZE = (1024, 576)


class ReadmeValidator(Protocol):
    def validate_readme_catalog(
        self, readme: str, skills: list[Skill]
    ) -> list[str]: ...


class ArtValidator(Protocol):
    def validate_png(self, path: Path, errors: list[str]) -> None: ...

    def validate_readme_art(
        self,
        readme: str,
        skills: list[Skill],
        errors: list[str],
    ) -> None: ...


class PackageValidator(Protocol):
    MAX_DESCRIPTION_CHARS: int
    MAX_TOTAL_DESCRIPTION_CHARS: int

    def read_description(self, entrypoint: Path) -> str: ...

    def description_budget_errors(
        self, descriptions: Mapping[str, str]
    ) -> list[str]: ...

    def validate(self, skills_root: Path) -> list[str]: ...


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
PACKAGE_VALIDATOR = cast(
    PackageValidator,
    load_script("validate-skills.py", "validate_skills_regression"),
)


def readme_skill_section(skill_name: str) -> str:
    """Build the exact public catalog/card block required for one skill."""

    return (
        "## Available Skills\n\n"
        "### Engineering\n\n"
        f"#### `{skill_name}`\n\n"
        f"`npx skills add jpcaparas/skills --skill {skill_name}`\n\n"
        '<p align="center">\n'
        f'  <img src="skills/engineering/{skill_name}/skill-card.png" '
        f'alt="16-bit side-scrolling pixel art badge for {skill_name}" '
        'width="480">\n'
        "</p>\n\n"
    )


def readme_with_section(section: str) -> str:
    """Place a catalog section after the required visible global command."""

    return f"# Test skills\n\n`npx skills add jpcaparas/skills`\n\n{section}"


class ReadmeCommentRegressionTests(unittest.TestCase):
    """Require catalog evidence to be visible rather than HTML-commented."""

    def test_visible_catalog_and_art_are_accepted(self) -> None:
        readme = readme_with_section(readme_skill_section("example"))

        catalog_errors = README_VALIDATOR.validate_readme_catalog(readme, [EXAMPLE])
        art_errors: list[str] = []
        ART_VALIDATOR.validate_readme_art(readme, [EXAMPLE], art_errors)

        self.assertEqual([], catalog_errors)
        self.assertEqual([], art_errors)

    def test_entire_commented_catalog_fails_both_validators(self) -> None:
        commented_section = f"<!--\n{readme_skill_section('example')}-->\n"
        readme = readme_with_section(commented_section)

        catalog_errors = README_VALIDATOR.validate_readme_catalog(readme, [EXAMPLE])
        art_errors: list[str] = []
        ART_VALIDATOR.validate_readme_art(readme, [EXAMPLE], art_errors)

        self.assertEqual(
            ["README.md is missing a '## Available Skills' section."],
            catalog_errors,
        )
        self.assertTrue(
            any(
                "exactly 1 skill-card PNG images; found 0" in error
                for error in art_errors
            ),
            art_errors,
        )

    def test_entire_fenced_catalog_fails_both_validators(self) -> None:
        fenced_section = f"```markdown\n{readme_skill_section('example')}```\n"
        readme = readme_with_section(fenced_section)

        catalog_errors = README_VALIDATOR.validate_readme_catalog(readme, [EXAMPLE])
        art_errors: list[str] = []
        ART_VALIDATOR.validate_readme_art(readme, [EXAMPLE], art_errors)

        self.assertEqual(
            ["README.md is missing a '## Available Skills' section."],
            catalog_errors,
        )
        self.assertTrue(
            any(
                "exactly 1 skill-card PNG images; found 0" in error
                for error in art_errors
            ),
            art_errors,
        )

    def test_commented_skill_header_is_not_catalog_evidence(self) -> None:
        visible_section = readme_skill_section("example")
        readme = readme_with_section(
            visible_section.replace(
                "#### `example`",
                "<!-- #### `example` -->",
                1,
            )
        )

        catalog_errors = README_VALIDATOR.validate_readme_catalog(readme, [EXAMPLE])

        self.assertTrue(
            any(
                "missing skill sections for: example" in error
                for error in catalog_errors
            ),
            catalog_errors,
        )

    def test_commented_skill_card_is_not_art_evidence(self) -> None:
        visible_section = readme_skill_section("example")
        card = (
            '<p align="center">\n'
            '  <img src="skills/engineering/example/skill-card.png" '
            'alt="16-bit side-scrolling pixel art badge for example" '
            'width="480">\n'
            "</p>"
        )
        readme = readme_with_section(
            visible_section.replace(card, f"<!--\n{card}\n-->", 1)
        )
        art_errors: list[str] = []

        ART_VALIDATOR.validate_readme_art(readme, [EXAMPLE], art_errors)

        self.assertTrue(
            any(
                "exactly 1 skill-card PNG images; found 0" in error
                for error in art_errors
            ),
            art_errors,
        )

    def test_html_comment_literal_in_fence_does_not_hide_visible_catalog(self) -> None:
        fenced_example = "```markdown\n<!-- example opener\n```\n\n"
        readme = readme_with_section(fenced_example + readme_skill_section("example"))

        catalog_errors = README_VALIDATOR.validate_readme_catalog(readme, [EXAMPLE])
        art_errors: list[str] = []
        ART_VALIDATOR.validate_readme_art(readme, [EXAMPLE], art_errors)

        self.assertEqual([], catalog_errors)
        self.assertEqual([], art_errors)


class NamespacedCatalogRegressionTests(unittest.TestCase):
    def test_correct_names_under_the_wrong_category_are_rejected(self) -> None:
        testing = Skill(
            "boundary-checks", "testing", Path("skills/testing/boundary-checks")
        )
        section = readme_skill_section("example")
        section += readme_skill_section("boundary-checks").split(
            "### Engineering\n\n", 1
        )[1]
        section += "### Testing\n\n"
        errors = README_VALIDATOR.validate_readme_catalog(
            readme_with_section(section), [EXAMPLE, testing]
        )
        self.assertTrue(
            any(
                "'boundary-checks' must be under category 'testing'" in error
                for error in errors
            ),
            errors,
        )

    def test_duplicate_and_missing_entries_and_wrong_install_commands_still_fail(
        self,
    ) -> None:
        section = readme_skill_section("example")
        cases = (
            (
                section + section.split("### Engineering\n\n", 1)[1],
                "duplicate skill headers",
            ),
            (
                section.replace("#### `example`", "#### `other`"),
                "missing skill sections for: example",
            ),
            (
                section.replace("--skill example", "--skill engineering/example"),
                "first non-empty line",
            ),
        )
        for content, diagnostic in cases:
            with self.subTest(diagnostic=diagnostic):
                errors = README_VALIDATOR.validate_readme_catalog(
                    readme_with_section(content), [EXAMPLE]
                )
                self.assertTrue(any(diagnostic in error for error in errors), errors)

    def test_card_in_another_category_cannot_satisfy_the_art_check(self) -> None:
        readme = readme_with_section(readme_skill_section("example")).replace(
            "skills/engineering/example/skill-card.png",
            "skills/testing/example/skill-card.png",
        )
        errors: list[str] = []
        ART_VALIDATOR.validate_readme_art(readme, [EXAMPLE], errors)
        self.assertTrue(
            any(
                "with path skills/engineering/example/skill-card.png" in error
                for error in errors
            ),
            errors,
        )

    def test_readme_refresh_keeps_images_and_copy_and_uses_namespace_paths(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="art refresh ") as directory:
            root = Path(directory)
            packages = (
                root / "skills/engineering/maintainable-code",
                root / "skills/fun/oneshot-timeline",
            )
            for package in packages:
                package.mkdir(parents=True)
                (package / "SKILL.md").write_text(
                    f"---\nname: {package.name}\ndescription: Test.\n---\n",
                    encoding="utf-8",
                )
                (package / "skill-card.png").write_bytes(b"preserve existing artwork")
            readme = readme_with_section(readme_skill_section("maintainable-code"))
            readme = readme.replace(
                "skills/engineering/maintainable-code/skill-card.png",
                "skills/testing/maintainable-code/skill-card.png",
            )
            readme += "Editorial description that must survive.\n\n### Fun\n\n"
            readme += readme_skill_section("oneshot-timeline").split(
                "### Engineering\n\n", 1
            )[1]
            readme_path = root / "README.md"
            readme_path.write_text(readme, encoding="utf-8")

            command = [
                sys.executable,
                str(SCRIPT_DIR / "render-skill-art.py"),
                "--repo-root",
                str(root),
                "--readme-only",
            ]
            result = subprocess.run(
                command, text=True, capture_output=True, check=False
            )

            self.assertEqual(0, result.returncode, result.stderr)
            updated = readme_path.read_text(encoding="utf-8")
            self.assertIn("Editorial description that must survive.", updated)
            self.assertIn(
                'src="skills/engineering/maintainable-code/skill-card.png"', updated
            )
            self.assertIn('src="skills/fun/oneshot-timeline/skill-card.png"', updated)
            self.assertEqual(2, updated.count('<img src="skills/'))
            for package in packages:
                self.assertEqual(
                    b"preserve existing artwork",
                    (package / "skill-card.png").read_bytes(),
                )
                self.assertEqual(
                    ["SKILL.md", "skill-card.png"],
                    sorted(path.name for path in package.iterdir()),
                )
            repeat = subprocess.run(
                command, text=True, capture_output=True, check=False
            )
            self.assertEqual(0, repeat.returncode, repeat.stderr)
            self.assertEqual(updated, readme_path.read_text(encoding="utf-8"))


class SkillCardImageTests(unittest.TestCase):
    """A card must be a fully decodable, metadata-free PNG of the README size."""

    def card_errors(self, write_card) -> list[str]:
        with tempfile.TemporaryDirectory(prefix="skill-card-") as directory:
            path = Path(directory) / "skill-card.png"
            write_card(path)
            errors: list[str] = []
            ART_VALIDATOR.validate_png(path, errors)
        return errors

    def test_accepts_a_clean_card(self) -> None:
        errors = self.card_errors(
            lambda path: Image.new("RGB", CARD_SIZE, "navy").save(path, "PNG")
        )

        self.assertEqual([], errors)

    def test_rejects_a_card_cut_off_mid_download(self) -> None:
        def write_truncated(path: Path) -> None:
            Image.radial_gradient("L").resize(CARD_SIZE).save(path, "PNG")
            complete = path.read_bytes()
            path.write_bytes(complete[: len(complete) // 2])

        errors = self.card_errors(write_truncated)

        self.assertEqual(1, len(errors), errors)
        self.assertIn("must be a decodable PNG image", errors[0])

    def test_rejects_a_card_too_heavy_for_the_readme(self) -> None:
        errors = self.card_errors(
            lambda path: Image.effect_noise(CARD_SIZE, 64).convert("RGB").save(path, "PNG")
        )

        self.assertEqual(1, len(errors), errors)
        self.assertIn("is larger than 750000 bytes", errors[0])

    def test_rejects_a_jpeg_saved_with_a_png_name(self) -> None:
        errors = self.card_errors(
            lambda path: Image.new("RGB", CARD_SIZE, "navy").save(path, "JPEG")
        )

        self.assertEqual(1, len(errors), errors)
        self.assertIn("must be a PNG image; found JPEG", errors[0])

    def test_rejects_the_unscaled_model_output_size(self) -> None:
        errors = self.card_errors(
            lambda path: Image.new("RGB", (1376, 768), "navy").save(path, "PNG")
        )

        self.assertEqual(1, len(errors), errors)
        self.assertIn("must be 1024x576; found 1376x768", errors[0])

    def test_rejects_generator_metadata(self) -> None:
        def write_with_metadata(path: Path) -> None:
            metadata = PngInfo()
            metadata.add_text("Software", "image generator")
            Image.new("RGB", CARD_SIZE, "navy").save(path, "PNG", pnginfo=metadata)

        errors = self.card_errors(write_with_metadata)

        self.assertEqual(1, len(errors), errors)
        self.assertIn("carries metadata (Software)", errors[0])


class DescriptionTests(unittest.TestCase):
    """Budget what hosts load: the description after YAML resolves it."""

    def read_description(self, content: str) -> str:
        with tempfile.TemporaryDirectory(prefix="skill-description-") as directory:
            entrypoint = Path(directory) / "SKILL.md"
            entrypoint.write_text(content, encoding="utf-8")
            return PACKAGE_VALIDATOR.read_description(entrypoint)

    def test_alias_and_block_scalars_resolve_to_the_text_hosts_load(self) -> None:
        cases = {
            "alias": (
                "---\nshared: &shared 'aliased text'\ndescription: *shared\n---\n",
                "aliased text",
            ),
            "folded": (
                "---\ndescription: >-\n  first line\n  second line\n---\n",
                "first line second line",
            ),
            "literal": (
                "---\ndescription: |-\n  first line\n  second line\n---\n",
                "first line\nsecond line",
            ),
        }

        for name, (content, expected) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(expected, self.read_description(content))

    def test_rejects_descriptions_a_host_cannot_use(self) -> None:
        cases = {
            "missing value": (
                "---\ndescription:\n---\n",
                "description must be a non-empty string",
            ),
            "quoted empty": (
                '---\ndescription: ""\n---\n',
                "description must be a non-empty string",
            ),
            "whitespace only": (
                "---\ndescription: '   '\n---\n",
                "description must be a non-empty string",
            ),
            "list": (
                "---\ndescription:\n  - list item\n---\n",
                "description must be a non-empty string",
            ),
            "duplicate key": (
                "---\ndescription: first\ndescription: second\n---\n",
                "duplicate key 'description'",
            ),
            "malformed YAML": (
                "---\ndescription: [unterminated\n---\n",
                "Invalid YAML frontmatter",
            ),
        }

        for name, (content, message) in cases.items():
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, message):
                    self.read_description(content)

    def test_budget_limits_are_inclusive(self) -> None:
        per_skill = PACKAGE_VALIDATOR.MAX_DESCRIPTION_CHARS
        at_limit = {"at-limit": "x" * per_skill}
        over_limit = {"over-limit": "x" * (per_skill + 1)}

        self.assertEqual([], PACKAGE_VALIDATOR.description_budget_errors(at_limit))
        self.assertEqual(
            [f"over-limit: description is {per_skill + 1} characters; the limit is {per_skill}."],
            PACKAGE_VALIDATOR.description_budget_errors(over_limit),
        )

    def test_total_budget_counts_every_skill(self) -> None:
        total = PACKAGE_VALIDATOR.MAX_TOTAL_DESCRIPTION_CHARS
        size = 400
        full = {f"skill-{index}": "x" * size for index in range(total // size)}
        remainder = total - size * len(full)
        full["remainder"] = "x" * remainder

        self.assertEqual([], PACKAGE_VALIDATOR.description_budget_errors(full))

        full["remainder"] += "x"
        errors = PACKAGE_VALIDATOR.description_budget_errors(full)

        self.assertEqual(1, len(errors), errors)
        self.assertIn(f"total {total + 1} characters", errors[0])


class PackageLayoutTests(unittest.TestCase):
    """A package must still work after an installer copies only its directory."""

    def package_errors(
        self, skill_markdown_body: str, files: Mapping[str, str]
    ) -> list[str]:
        with tempfile.TemporaryDirectory(prefix="skill-package-") as directory:
            skills_root = Path(directory) / "skills"
            package = skills_root / "engineering/example"
            package.mkdir(parents=True)
            (package / "SKILL.md").write_text(
                "---\nname: example\ndescription: Example.\n---\n\n"
                + skill_markdown_body,
                encoding="utf-8",
            )
            (skills_root / "shared.md").write_text("shared", encoding="utf-8")
            for relative, content in files.items():
                path = package / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            return PACKAGE_VALIDATOR.validate(skills_root)

    def test_accepts_links_that_resolve_inside_the_package(self) -> None:
        body = (
            "Read [the guide](references/guide.md#setup), "
            "[a spaced name](references/two%20words.md), "
            "[the docs](https://example.com/docs), [a heading](#usage) "
            "and `[not a link](missing.md)`.\n\n"
            "```markdown\n[example only](also-missing.md)\n```\n"
        )
        files = {
            "references/guide.md": "guide",
            "references/two words.md": "spaced",
        }

        self.assertEqual([], self.package_errors(body, files))

    def test_rejects_a_link_to_a_file_the_package_does_not_ship(self) -> None:
        errors = self.package_errors("See [the guide](references/guide.md).\n", {})

        self.assertEqual(1, len(errors), errors)
        self.assertIn("linked file does not exist: references/guide.md", errors[0])

    def test_rejects_a_link_to_an_existing_file_outside_the_package(self) -> None:
        errors = self.package_errors("See [shared notes](../../shared.md).\n", {})

        self.assertEqual(1, len(errors), errors)
        self.assertIn("link leaves the package", errors[0])

    def test_rejects_a_fixture_that_hosts_would_install_as_a_skill(self) -> None:
        errors = self.package_errors(
            "", {"evals/files/broken/SKILL.md": "not an installable package"}
        )

        self.assertEqual(1, len(errors), errors)
        self.assertIn("rename evals/files/broken/SKILL.md", errors[0])

    def test_accepts_the_same_fixture_under_another_filename(self) -> None:
        errors = self.package_errors(
            "", {"evals/files/broken/SKILL.fixture.md": "not an installable package"}
        )

        self.assertEqual([], errors)

    def test_rejects_a_shipped_script_that_does_not_compile(self) -> None:
        broken = "def broken(:\n"
        errors = self.package_errors(
            "",
            {"scripts/probe.py": broken, "evals/files/broken.py": broken},
        )

        self.assertEqual(1, len(errors), errors)
        self.assertIn("scripts/probe.py: does not compile", errors[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
