#!/usr/bin/env python3
"""Check package integrity and validator regressions; does not run model evals."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import validate


class PackageTests(unittest.TestCase):
    source: Path

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="idiomatic-package-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "idiomatic"
        shutil.copytree(
            self.source,
            self.root,
            ignore=shutil.ignore_patterns("__pycache__", "*.png"),
        )
        self.evals_path = self.root / "evals/evals.json"
        self.payload = validate.mapping(
            json.loads(self.evals_path.read_text(encoding="utf-8"))
        )

    def write_evals(self) -> None:
        self.evals_path.write_text(json.dumps(self.payload), encoding="utf-8")

    def test_standalone_package_needs_no_sibling_skills(self) -> None:
        self.assertEqual(validate.validate(self.root), [])

    def test_empty_evals_cannot_pass_as_behavioural_coverage(self) -> None:
        self.payload["evals"] = []
        self.write_evals()
        self.assertIn(
            "behavioural evals must not be empty", validate.validate(self.root)
        )

    def test_duplicate_ids_cannot_hide_a_case(self) -> None:
        cases = validate.items(self.payload["evals"])
        cases.append(cases[0])
        self.payload["evals"] = cases
        self.write_evals()
        self.assertIn(
            "eval IDs must be unique positive integers", validate.validate(self.root)
        )

    def test_untyped_assertions_do_not_count_as_gradable_expectations(self) -> None:
        cases = [
            validate.mapping(case) for case in validate.items(self.payload["evals"])
        ]
        cases[0]["assertions"] = [{"text": "A useful plan"}]
        self.payload["evals"] = cases
        self.write_evals()
        self.assertIn("eval 1: invalid typed assertion", validate.validate(self.root))

    def test_fixtures_must_exist_inside_the_installed_package(self) -> None:
        outside = self.root.parent / "private.txt"
        outside.write_text("not a package fixture", encoding="utf-8")
        cases = [
            validate.mapping(case) for case in validate.items(self.payload["evals"])
        ]
        for relative in ("evals/files/missing.md", "../private.txt", str(outside)):
            with self.subTest(relative=relative):
                cases[0]["files"] = [relative]
                self.payload["evals"] = cases
                self.write_evals()
                self.assertIn(
                    "eval 1: missing or escaping fixture", validate.validate(self.root)
                )

    def test_reference_links_cannot_escape_through_a_symlink(self) -> None:
        outside = self.root.parent / "external.md"
        outside.write_text("external", encoding="utf-8")
        reference = self.root / "references/production-data.md"
        reference.unlink()
        reference.symlink_to(outside)
        self.assertIn(
            "missing or escaping file: references/production-data.md",
            validate.validate(self.root),
        )

    def test_trigger_expectations_must_be_boolean(self) -> None:
        path = self.root / "evals/trigger-evals.json"
        path.write_text(
            json.dumps(
                [
                    {"query": "Align this workspace", "should_trigger": "false"},
                    {"query": "Format one file", "should_trigger": False},
                ]
            ),
            encoding="utf-8",
        )
        self.assertIn(
            "trigger requires query and boolean should_trigger",
            validate.validate(self.root),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_path", type=Path)
    root = parser.parse_args().skill_path.resolve()
    errors = validate.validate(root)
    if errors:
        print("\n".join(errors))
        return 1
    PackageTests.source = root
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(PackageTests)
    )
    print(
        "Package/schema checks only; model outputs and trigger decisions were not executed."
    )
    return int(not result.wasSuccessful())


if __name__ == "__main__":
    raise SystemExit(main())
