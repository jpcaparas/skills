#!/usr/bin/env python3
"""Namespace regressions: complete discovery without publishing fixture skills."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from skill_catalog import discover_skills


class SkillCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="skill catalogue ")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "skills"
        self.root.mkdir()

    def package(self, category: str, name: str) -> Path:
        path = self.root / category / name
        path.mkdir(parents=True)
        (path / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: Test skill.\n---\n", encoding="utf-8"
        )
        return path

    def test_discovers_multiple_categories_but_never_nested_eval_skills(self) -> None:
        beta = self.package("testing", "beta")
        alpha = self.package("engineering", "alpha")
        fixture = beta / "evals/files/broken-skill"
        fixture.mkdir(parents=True)
        (fixture / "SKILL.md").write_text(
            "Deliberately invalid fixture.", encoding="utf-8"
        )

        skills = discover_skills(self.root)

        self.assertEqual(
            [("engineering", "alpha", alpha), ("testing", "beta", beta)],
            [(skill.category, skill.name, skill.directory) for skill in skills],
        )
        self.assertEqual("skills/engineering/alpha", skills[0].repo_path)

    def test_duplicate_install_names_across_categories_fail_instead_of_deduplicating(
        self,
    ) -> None:
        self.package("engineering", "same-name")
        self.package("testing", "same-name")
        with self.assertRaisesRegex(ValueError, "Duplicate skill name 'same-name'"):
            discover_skills(self.root)

    def test_missing_entrypoint_cannot_silently_remove_a_package_from_the_gauntlet(
        self,
    ) -> None:
        self.package("testing", "present")
        (self.root / "testing" / "missing").mkdir()
        with self.assertRaisesRegex(ValueError, "Missing regular SKILL.md"):
            discover_skills(self.root)

    def test_rejects_flat_leftovers_and_unknown_categories(self) -> None:
        for directory in ("old-flat-skill", "unregistered-category"):
            with self.subTest(directory=directory):
                path = self.root / directory
                path.mkdir()
                with self.assertRaisesRegex(
                    ValueError, "Unknown category or unnamespaced skill"
                ):
                    discover_skills(self.root)
                path.rmdir()

    def test_rejects_container_entrypoints_that_shadow_the_inventory(self) -> None:
        self.package("engineering", "visible")
        for container in (self.root, self.root / "engineering"):
            with self.subTest(container=container):
                entrypoint = container / "SKILL.md"
                entrypoint.write_text("A container is not a skill.", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "would hide nested skills"):
                    discover_skills(self.root)
                entrypoint.unlink()

    def test_rejects_symlinks_at_every_inventory_boundary_including_dangling_links(
        self,
    ) -> None:
        self.package("engineering", "real")
        for boundary in (
            self.root / "testing",
            self.root / "engineering" / "alias",
            self.root / "engineering" / "broken" / "SKILL.md",
        ):
            with self.subTest(boundary=boundary):
                boundary.parent.mkdir(parents=True, exist_ok=True)
                boundary.symlink_to(self.root / "does-not-exist")
                with self.assertRaisesRegex(ValueError, "must not be a symlink"):
                    discover_skills(self.root)
                boundary.unlink()

    def test_rejects_name_mismatch_and_duplicate_yaml_keys(self) -> None:
        path = self.package("testing", "example") / "SKILL.md"
        for frontmatter, error in (
            ("name: different", "must match directory"),
            ("name: example\nname: example", "duplicate key 'name'"),
            ("name: [unterminated", "Invalid YAML frontmatter"),
        ):
            with self.subTest(frontmatter=frontmatter):
                path.write_text(f"---\n{frontmatter}\n---\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, error):
                    discover_skills(self.root)

    def test_empty_inventory_and_empty_categories_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "No installable skills"):
            discover_skills(self.root)
        (self.root / "testing").mkdir()
        with self.assertRaisesRegex(ValueError, "Empty skill category"):
            discover_skills(self.root)

    def test_cli_failure_emits_no_partial_inventory(self) -> None:
        self.package("engineering", "valid-first")
        self.package("testing", "broken-last").joinpath("SKILL.md").unlink()
        result = self.cli()
        self.assertEqual(1, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertIn("Missing regular SKILL.md", result.stderr)

    def test_cli_paths_with_spaces_and_stable_names(self) -> None:
        beta = self.package("engineering", "beta")
        alpha = self.package("testing", "alpha")
        paths = self.cli()
        names = self.cli("--names")
        self.assertEqual(0, paths.returncode, paths.stderr)
        self.assertEqual([str(beta), str(alpha)], paths.stdout.splitlines())
        self.assertEqual(0, names.returncode, names.stderr)
        self.assertEqual(["alpha", "beta"], names.stdout.splitlines())

    def cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("skill_catalog.py")),
                "--skills-root",
                str(self.root),
                *args,
            ],
            text=True,
            capture_output=True,
            check=False,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
