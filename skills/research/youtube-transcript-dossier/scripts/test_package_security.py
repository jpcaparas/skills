#!/usr/bin/env python3
"""Check that package inspection cannot select outside files or executable code."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from test_skill import is_package_file, load_fetch_module, test_skill


class PackageBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.package = self.root / "package"
        self.package.mkdir()
        (self.package / "references").mkdir()
        self.document = self.package / "references/guide.md"
        self.document.write_text("Guide\n", encoding="utf-8")
        self.outside = self.root / "package-sibling"
        self.outside.mkdir()
        self.outside_file = self.outside / "outside.md"
        self.outside_file.write_text("Outside\n", encoding="utf-8")

    def test_internal_files_are_accepted_but_escaped_and_missing_files_are_not(self) -> None:
        (self.package / "references/inside.md").symlink_to(self.document)
        (self.package / "references/outside.md").symlink_to(self.outside_file)
        cases = [
            ("references/guide.md", True),
            ("references/inside.md", True),
            ("references/outside.md", False),
            ("../package-sibling/outside.md", False),
            (str(self.outside_file), False),
            ("references/missing.md", False),
            ("references", False),
        ]
        for reference, expected in cases:
            with self.subTest(reference=reference):
                self.assertEqual(expected, is_package_file(str(self.package), reference))

    def test_foreign_helper_is_rejected_before_its_module_body_runs(self) -> None:
        scripts = self.package / "scripts"
        scripts.mkdir()
        marker = self.root / "executed"
        (scripts / "fetch_transcript.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "own package"):
            load_fetch_module(str(self.package))

        self.assertFalse(marker.exists())

    def test_eval_and_markdown_references_cannot_count_outside_files_as_valid(self) -> None:
        (self.package / "evals").mkdir()
        (self.package / "evals/evals.json").write_text(json.dumps({
            "evals": [{
                "id": 1, "name": "outside", "prompt": "Example",
                "expected_output": "Example", "files": [str(self.outside_file)],
            }],
        }), encoding="utf-8")
        (self.package / "SKILL.md").write_text(
            "Read `references/../../package-sibling/outside.md`.\n",
            encoding="utf-8",
        )

        result = test_skill(str(self.package))

        self.assertFalse(result["passed"])
        self.assertEqual({"passed": 0, "total": 1}, result["files_verified"])
        self.assertEqual({"passed": 0, "total": 1}, result["cross_references"])
        self.assertTrue(any("referenced file missing or outside" in error for error in result["errors"]))
        self.assertTrue(any("Cross-reference missing or outside" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
