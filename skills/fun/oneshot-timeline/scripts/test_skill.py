#!/usr/bin/env python3
"""Regression tests for the standalone oneshot-timeline package validator."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from validate import JsonValue


VALIDATOR = Path(__file__).with_name("validate.py")


class ValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "fun" / "oneshot-timeline"
        for directory in ("references", "evals/files", "scripts"):
            (self.root / directory).mkdir(parents=True, exist_ok=True)
        self.write("SKILL.md", "---\nname: oneshot-timeline\ndescription: A useful test skill.\n---\n\nRead [media](references/media.md).\n")
        self.write("README.md", "# Wrapper\n")
        self.write("AGENTS.md", "# Wrapper\n")
        self.write("references/media.md", "# Media\n")
        self.write("evals/files/dns-facts.md", "# DNS\n")
        self.write("evals/files/leaseco-evidence.md", "# LeaseCo\n")
        self.write("scripts/validate.py", "# fixture\n")
        self.write("scripts/test_skill.py", "# fixture\n")
        self.write_json("metadata.json", {"name": "oneshot-timeline", "entrypoint": "SKILL.md", "category": "fun"})
        self.write_json("evals/evals.json", self.evals())
        self.write_json("evals/trigger-evals.json", [
            {"query": "Build an explainer timeline site", "should_trigger": True},
            {"query": "Write plain prose", "should_trigger": False},
        ])

    def write(self, relative: str, text: str) -> None:
        (self.root / relative).write_text(text, encoding="utf-8")

    def write_json(self, relative: str, value: JsonValue) -> None:
        self.write(relative, json.dumps(value))

    def evals(self) -> dict[str, JsonValue]:
        return {"skill_name": "oneshot-timeline", "evals": [{
            "id": 1, "name": "case", "prompt": "Do it", "expected_output": "Result",
            "files": ["evals/files/dns-facts.md"], "tags": ["smoke"],
            "assertions": [{"type": "functional", "text": "Works"}],
        }]}

    def validate(self) -> tuple[int, str]:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(self.root)],
            check=False, capture_output=True, text=True,
        )
        return result.returncode, result.stdout + result.stderr

    def test_positive_minimal_package(self) -> None:
        code, output = self.validate()
        self.assertEqual((0, True), (code, '"valid": true' in output))

    def test_installed_package_accepts_dot_outside_catalog_layout(self) -> None:
        installed = Path(self.temporary.name) / "installed" / "oneshot-timeline"
        installed.parent.mkdir()
        self.root.rename(installed)
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "."], cwd=installed,
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_json_null_is_not_a_valid_document(self) -> None:
        for path in ("metadata.json", "evals/evals.json", "evals/trigger-evals.json"):
            with self.subTest(path=path):
                original = (self.root / path).read_text(encoding="utf-8")
                self.write(path, "null")
                code, output = self.validate()
                self.assertEqual(1, code, output)
                self.assertIn(f"{path} must", output)
                self.write(path, original)

    def test_missing_linked_file(self) -> None:
        self.write("SKILL.md", "---\nname: oneshot-timeline\ndescription: Test.\n---\n[missing](references/nope.md)\n")
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("Local Markdown reference", output)

    def test_empty_link_reports_an_error_not_a_traceback(self) -> None:
        self.write("README.md", "[missing]( )\n")
        code, output = self.validate()
        self.assertEqual(1, code)
        self.assertIn("Empty Markdown reference", output)
        self.assertNotIn("Traceback", output)

    def test_escaping_fixture(self) -> None:
        data = self.evals()
        cases = data["evals"]
        assert isinstance(cases, list) and isinstance(cases[0], dict)
        cases[0]["files"] = ["../../outside.md"]
        self.write_json("evals/evals.json", data)
        self.assertIn("escapes package", self.validate()[1])

    def test_symlink_fixture_escape(self) -> None:
        outside = Path(self.temporary.name) / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        (self.root / "evals/files/dns-facts.md").unlink()
        (self.root / "evals/files/dns-facts.md").symlink_to(outside)
        self.assertIn("escapes package", self.validate()[1])

    def test_malformed_json_and_assertion_type(self) -> None:
        self.write("metadata.json", "{")
        data = self.evals()
        cases = data["evals"]
        assert isinstance(cases, list) and isinstance(cases[0], dict)
        cases[0]["assertions"] = [{"type": 7, "text": "bad"}]
        self.write_json("evals/evals.json", data)
        output = self.validate()[1]
        self.assertIn("Invalid JSON in metadata.json", output)
        self.assertIn("invalid type", output)

    def test_duplicate_and_boolean_ids(self) -> None:
        for invalid_id in (1, True):
            with self.subTest(invalid_id=invalid_id):
                data = self.evals()
                cases = data["evals"]
                assert isinstance(cases, list) and isinstance(cases[0], dict)
                invalid = dict(cases[0])
                invalid["id"] = invalid_id
                cases.append(invalid)
                self.write_json("evals/evals.json", data)
                code, output = self.validate()
                self.assertEqual(1, code)
                self.assertIn("Eval 2 id must be a unique integer", output)

    def test_all_positive_triggers(self) -> None:
        self.write_json("evals/trigger-evals.json", [{"query": "Timeline", "should_trigger": True}])
        self.assertIn("positive and negative", self.validate()[1])


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {Path(argv[0]).name} <skill-path>", file=sys.stderr)
        return 2
    package = Path(argv[1])
    if not package.is_dir():
        print(f"Skill path is not a directory: {package}", file=sys.stderr)
        return 1
    result = subprocess.run([sys.executable, str(VALIDATOR), str(package)], check=False)
    if result.returncode != 0:
        return 1
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ValidatorTests)
    return 0 if unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
