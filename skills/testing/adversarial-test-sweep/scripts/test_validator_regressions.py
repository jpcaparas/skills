#!/usr/bin/env python3
"""Regression tests for adversarial-test-sweep package evidence."""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from test_skill import (
    PreflightResult,
    verify_fixture_contract,
    verify_validator_regressions,
)
from validate import validate_skill


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_RELATIVE_PATH = Path("evals/fixtures/parser-weak-oracle")
DESCRIPTION_FRONTMATTER_LINE = (
    'description: "Run a bounded adversarial sweep of an existing test suite. '
    "Use to harden a suite or subsystem against malformed inputs, boundaries, "
    "invalid state, races, dependency/resource failures, weak or redundant tests, "
    "flakes, and missing durable regressions. Skip ordinary test additions, load, "
    'chaos, and penetration testing."'
)


@contextmanager
def copied_package() -> Iterator[Path]:
    """Yield an isolated package copy that each adversarial case may mutate."""

    with tempfile.TemporaryDirectory(prefix="adversarial-sweep-regression-") as temp_dir:
        root = Path(temp_dir) / PACKAGE_ROOT.name
        shutil.copytree(PACKAGE_ROOT, root)
        yield root


def assert_package_rejected(test: unittest.TestCase, root: Path) -> None:
    """Require the package validator to return structured negative evidence."""

    result = validate_skill(str(root))
    test.assertIs(result.get("valid"), False)
    errors = result.get("errors")
    test.assertIsInstance(errors, list)
    test.assertTrue(errors)


class PackageValidatorRegressionTests(unittest.TestCase):
    """Reject package mutations that previously produced false-green releases."""

    def test_accepts_the_committed_package(self) -> None:
        result = validate_skill(str(PACKAGE_ROOT))

        self.assertIs(result.get("valid"), True)
        self.assertEqual([], result.get("errors"))

    def test_rejects_an_unterminated_frontmatter_description(self) -> None:
        with copied_package() as root:
            skill_path = root / "SKILL.md"
            content = skill_path.read_text(encoding="utf-8")
            content = content.replace(
                DESCRIPTION_FRONTMATTER_LINE,
                'description: "Run a bounded adversarial sweep of an existing test suite.',
                1,
            )
            skill_path.write_text(content, encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_a_version_nested_below_metadata_version(self) -> None:
        with copied_package() as root:
            skill_path = root / "SKILL.md"
            content = skill_path.read_text(encoding="utf-8").replace(
                'metadata:\n  version: "1.0.0"',
                'metadata:\n  release:\n    version: "1.0.0"',
                1,
            )
            skill_path.write_text(content, encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_duplicate_json_members(self) -> None:
        with copied_package() as root:
            metadata_path = root / "metadata.json"
            content = metadata_path.read_text(encoding="utf-8").replace(
                "{\n",
                '{\n  "name": "wrong-name",\n',
                1,
            )
            metadata_path.write_text(content, encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_nonstandard_json_constants(self) -> None:
        with copied_package() as root:
            metadata_path = root / "metadata.json"
            content = metadata_path.read_text(encoding="utf-8").replace(
                "\n}",
                ',\n  "not_json": NaN\n}',
                1,
            )
            metadata_path.write_text(content, encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_invalid_agent_manifest_yaml(self) -> None:
        with copied_package() as root:
            (root / "agents/openai.yaml").write_text(
                'interface: [\n'
                '  display_name: "Adversarial Test Sweep"\n'
                '  short_description: "Still present as raw text"\n'
                '  default_prompt: "Still present as raw text"\n',
                encoding="utf-8",
            )

            assert_package_rejected(self, root)

    def test_rejects_duplicate_eval_tags(self) -> None:
        with copied_package() as root:
            evals_path = root / "evals/evals.json"
            payload = json.loads(evals_path.read_text(encoding="utf-8"))
            payload["evals"][0]["tags"].append(payload["evals"][0]["tags"][0])
            evals_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_duplicate_assertions(self) -> None:
        with copied_package() as root:
            evals_path = root / "evals/evals.json"
            payload = json.loads(evals_path.read_text(encoding="utf-8"))
            payload["evals"][1]["assertions"].append(
                payload["evals"][0]["assertions"][0]
            )
            evals_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_duplicate_eval_prompts_after_normalization(self) -> None:
        with copied_package() as root:
            evals_path = root / "evals/evals.json"
            payload = json.loads(evals_path.read_text(encoding="utf-8"))
            prompt = payload["evals"][0]["prompt"]
            payload["evals"][1]["prompt"] = f"  {prompt.upper()}  "
            evals_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_semantically_duplicate_trigger_queries(self) -> None:
        with copied_package() as root:
            triggers_path = root / "evals/trigger-evals.json"
            payload = json.loads(triggers_path.read_text(encoding="utf-8"))
            query = payload[0]["query"]
            payload[1]["query"] = f"  {query.upper()}  "
            triggers_path.write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )

            assert_package_rejected(self, root)

    def test_rejects_frontmatter_yaml_aliases(self) -> None:
        with copied_package() as root:
            skill_path = root / "SKILL.md"
            content = skill_path.read_text(encoding="utf-8").replace(
                "metadata:\n  version:",
                "metadata: &release\n  version:",
                1,
            )
            skill_path.write_text(content, encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_invalid_plain_frontmatter_scalar(self) -> None:
        with copied_package() as root:
            skill_path = root / "SKILL.md"
            content = skill_path.read_text(encoding="utf-8").replace(
                DESCRIPTION_FRONTMATTER_LINE,
                "description: valid-looking: but-invalid-yaml",
                1,
            )
            skill_path.write_text(content, encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_invalid_plain_agent_scalar(self) -> None:
        with copied_package() as root:
            manifest_path = root / "agents/openai.yaml"
            content = manifest_path.read_text(encoding="utf-8").replace(
                'display_name: "Adversarial Test Sweep"',
                "display_name: valid-looking: but-invalid-yaml",
                1,
            )
            manifest_path.write_text(content, encoding="utf-8")

            assert_package_rejected(self, root)

    def test_requires_each_workflow_phase_to_own_its_completion_gate(self) -> None:
        with copied_package() as root:
            skill_path = root / "SKILL.md"
            content = skill_path.read_text(encoding="utf-8")
            content = content.replace("**Complete when:**", "**Phase complete:**")
            replacement = ("\n**Complete when:** displaced marker\n" * 9) + "\n## Gotchas"
            content = content.replace("\n## Gotchas", replacement, 1)
            skill_path.write_text(content, encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_a_held_out_probe_in_public_eval_files(self) -> None:
        with copied_package() as root:
            evals_path = root / "evals/evals.json"
            payload = json.loads(evals_path.read_text(encoding="utf-8"))
            payload["evals"][0]["files"].append(
                "evals/fixtures/parser-weak-oracle/check_duplicate_header.py"
            )
            evals_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_a_non_fixture_file_as_behavioral_evidence(self) -> None:
        with copied_package() as root:
            evals_path = root / "evals/evals.json"
            payload = json.loads(evals_path.read_text(encoding="utf-8"))
            payload["evals"][0]["files"] = ["README.md"]
            evals_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

            assert_package_rejected(self, root)

    def test_rejects_modified_fixture_content(self) -> None:
        with copied_package() as root:
            fixture_path = root / FIXTURE_RELATIVE_PATH / "test_invoice_parser.py"
            fixture_path.write_text(
                fixture_path.read_text(encoding="utf-8") + "\n# weakened evidence\n",
                encoding="utf-8",
            )

            assert_package_rejected(self, root)

    def test_rejects_a_missing_standard_markdown_link(self) -> None:
        with copied_package() as root:
            readme_path = root / "README.md"
            readme_path.write_text(
                readme_path.read_text(encoding="utf-8")
                + "\n[Missing reference](references/does-not-exist.md)\n",
                encoding="utf-8",
            )

            assert_package_rejected(self, root)

    def test_rejects_a_local_reference_that_resolves_to_a_directory(self) -> None:
        with copied_package() as root:
            readme_path = root / "README.md"
            readme_path.write_text(
                readme_path.read_text(encoding="utf-8")
                + "\n`references/../references`\n",
                encoding="utf-8",
            )

            assert_package_rejected(self, root)

    def test_reports_invalid_utf8_as_a_structured_error(self) -> None:
        with copied_package() as root:
            (root / "README.md").write_bytes(b"invalid UTF-8: \xff\n")

            assert_package_rejected(self, root)


class FixtureOracleRegressionTests(unittest.TestCase):
    """Require the committed fixture to execute the intended discriminating tests."""

    def test_rejects_a_fully_skipped_baseline_suite(self) -> None:
        with copied_package() as root:
            test_path = root / FIXTURE_RELATIVE_PATH / "test_invoice_parser.py"
            content = test_path.read_text(encoding="utf-8").replace(
                "class InvoiceHeaderTests(unittest.TestCase):",
                '@unittest.skip("disabled")\nclass InvoiceHeaderTests(unittest.TestCase):',
                1,
            )
            test_path.write_text(content, encoding="utf-8")
            result = PreflightResult(skill_name=root.name)

            verify_fixture_contract(root, result)

            self.assertFalse(result.fixture_contract_verified)
            self.assertTrue(result.errors)

    def test_rejects_spoofed_unittest_summary_text(self) -> None:
        with copied_package() as root:
            fixture = root / FIXTURE_RELATIVE_PATH
            (fixture / "test_invoice_parser.py").write_text(
                '"""Print the expected count while running one unrelated test."""\n'
                "import unittest\n"
                'print("Ran 3 tests")\n'
                "class UnrelatedTest(unittest.TestCase):\n"
                "    def test_unrelated(self) -> None:\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )
            (fixture / "check_duplicate_header.py").write_text(
                '"""Print a failure transcript without testing the parser."""\n'
                'print("Ran 1 test")\n'
                'print("HeaderError not raised")\n'
                'print("FAILED (failures=1)")\n'
                "raise SystemExit(1)\n",
                encoding="utf-8",
            )
            result = PreflightResult(skill_name=root.name)

            verify_fixture_contract(root, result)

            self.assertFalse(result.fixture_contract_verified)
            self.assertTrue(result.errors)

    def test_rejects_spoofed_validator_regression_summary_text(self) -> None:
        with copied_package() as root:
            regression_path = root / "scripts/test_validator_regressions.py"
            regression_path.write_text(
                'print("Ran 21 tests in 0.001s")\nprint("OK")\n',
                encoding="utf-8",
            )
            result = PreflightResult(skill_name=root.name)

            verify_validator_regressions(root, result)

            self.assertFalse(result.validator_regressions_verified)
            self.assertTrue(result.errors)

    def test_rejects_noop_validator_regression_suite(self) -> None:
        with copied_package() as root:
            regression_path = root / "scripts/test_validator_regressions.py"
            regression_path.write_text(
                """\
import unittest
from test_skill import VALIDATOR_REGRESSION_TEST_OUTCOMES

classes = {}
for test_id in VALIDATOR_REGRESSION_TEST_OUTCOMES:
    _, class_name, method_name = test_id.split('.')
    methods = classes.setdefault(class_name, {})
    methods[method_name] = lambda self: None
for class_name, methods in classes.items():
    globals()[class_name] = type(class_name, (unittest.TestCase,), methods)
""",
                encoding="utf-8",
            )
            result = PreflightResult(skill_name=root.name)

            verify_validator_regressions(root, result)

            self.assertFalse(result.validator_regressions_verified)
            self.assertTrue(result.errors)


if __name__ == "__main__":
    unittest.main()
