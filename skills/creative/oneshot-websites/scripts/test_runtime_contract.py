"""Shared safety rules: consent resolution, bounded metadata reads, identity keys."""

from __future__ import annotations

import hashlib
import os
import tempfile
import unittest
from pathlib import Path

import runtime_contract as rc


def receipt_and_run(mode: str = "gauntlet") -> tuple[dict, dict]:
    receipt = {
        "schemaVersion": "2.5",
        "runSchemaVersion": "3.5",
        "verificationMode": mode,
        "qualityGauntlet": {"required": mode == "gauntlet", "contractVersion": "1.0", "reportSchemaVersion": "2.1"},
        "directionalControls": {"required": False, "technicalPrompt": None, "evidencePath": None},
    }
    return receipt, {"schemaVersion": "3.5", "verificationMode": mode}


class VerificationModeTests(unittest.TestCase):
    def test_matching_receipt_run_and_report_resolve_to_the_receipt_mode(self) -> None:
        for mode in ("gauntlet", "none"):
            receipt, run = receipt_and_run(mode)
            self.assertEqual(rc.verification_mode(receipt, run, {"verificationMode": mode}), mode)

    def test_worker_cannot_flip_mode_in_run_or_report(self) -> None:
        receipt, run = receipt_and_run("gauntlet")
        run["verificationMode"] = "none"
        with self.assertRaisesRegex(ValueError, "run verificationMode must match"):
            rc.verification_mode(receipt, run)
        receipt, run = receipt_and_run("gauntlet")
        with self.assertRaisesRegex(ValueError, "report verificationMode must match"):
            rc.verification_mode(receipt, run, {"verificationMode": "none"})

    def test_missing_or_unknown_mode_is_never_an_opt_out(self) -> None:
        receipt, run = receipt_and_run()
        del receipt["verificationMode"]
        with self.assertRaises(ValueError):
            rc.verification_mode(receipt, run)
        receipt, run = receipt_and_run()
        receipt["verificationMode"] = run["verificationMode"] = "skip"
        with self.assertRaises(ValueError):
            rc.verification_mode(receipt, run)

    def test_old_schemas_are_not_accepted(self) -> None:
        receipt, run = receipt_and_run()
        receipt["schemaVersion"] = "2.4"
        with self.assertRaisesRegex(ValueError, "receipt 2.5 and run 3.5"):
            rc.verification_mode(receipt, run)

    def test_receipt_gauntlet_flag_must_agree_with_mode(self) -> None:
        receipt, run = receipt_and_run("none")
        receipt["qualityGauntlet"]["required"] = True
        with self.assertRaisesRegex(ValueError, "must agree with verificationMode"):
            rc.verification_mode(receipt, run)

    def test_generation_only_cannot_require_directional_verification(self) -> None:
        receipt, run = receipt_and_run("none")
        receipt["directionalControls"]["required"] = True
        with self.assertRaisesRegex(ValueError, "cannot require directional"):
            rc.verification_mode(receipt, run)


class UnverifiedReportTests(unittest.TestCase):
    def test_generation_only_report_must_not_claim_verification(self) -> None:
        good = {"artifact": {"staticDeploymentVerified": False}, "verification": [], "qualityGauntlet": None}
        rc.require_unverified_report(good)
        for change in (
            {"artifact": {"staticDeploymentVerified": True}},
            {"verification": [{"kind": "x", "result": "passed", "evidence": "y"}]},
            {"qualityGauntlet": {}},
            {"artifact": None},
        ):
            with self.assertRaises(ValueError, msg=change):
                rc.require_unverified_report({**good, **change})


class PassedVerificationTests(unittest.TestCase):
    def test_needs_passing_result_kind_and_evidence(self) -> None:
        ok = {"kind": "smoke", "result": "Passed", "evidence": "opened"}
        self.assertTrue(rc.is_passed_verification(ok))
        self.assertTrue(rc.is_passed_verification({**ok, "result": "ok"}))
        for bad in (
            {**ok, "result": "failed"},
            {**ok, "kind": " "},
            {**ok, "evidence": ""},
            {**ok, "evidence": None},
            {"result": "passed"},
            "passed",
            None,
        ):
            self.assertFalse(rc.is_passed_verification(bad), bad)


class MojibakeTests(unittest.TestCase):
    def test_valid_text_passes_and_each_corruption_shape_is_flagged_at_its_offset(self) -> None:
        for sample in ("— – ‘single’ “double” … café naïve", "日本語 العربية 🚀", "Icelandic orð—dash"):
            self.assertIsNone(rc.find_likely_mojibake(sample), sample)
        evidence = rc.find_likely_mojibake("ab â€” cd")
        self.assertEqual((evidence.offset, evidence.codepoints), (3, "U+00E2 U+20AC U+201D"))
        for sample in ("cafÃ©", "ðŸš€", "x\ufffdy", "stray\u0081"):
            self.assertIsNotNone(rc.find_likely_mojibake(sample), sample)


class JsonBoundsTests(unittest.TestCase):
    def test_nesting_limit_boundary(self) -> None:
        depth = rc.JSON_NESTING_MAX
        self.assertEqual(rc.parse_json_bounded("[" * depth + "]" * depth) is not None, True)
        with self.assertRaisesRegex(ValueError, "nesting exceeds"):
            rc.parse_json_bounded("[" * (depth + 1) + "]" * (depth + 1))

    def test_brackets_inside_strings_do_not_count_as_nesting(self) -> None:
        self.assertEqual(rc.parse_json_bounded('{"a": "' + "[" * 1000 + '\\"[["}')["a"][:1], "[")

    def test_duplicate_members_nan_and_huge_numbers_are_rejected(self) -> None:
        for text in ('{"a":1,"a":2}', "NaN", "[Infinity]", "[" + "9" * 300 + "]", "[1." + "0" * 300 + "]"):
            with self.assertRaises(ValueError, msg=text[:30]):
                rc.parse_json_bounded(text)
        self.assertEqual(rc.parse_json_bounded('{"a": 1.5, "b": [2]}'), {"a": 1.5, "b": [2]})


class BoundedReadTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)

    def test_exact_limit_reads_and_one_over_fails(self) -> None:
        path = self.dir / "f"
        path.write_bytes(b"x" * 10)
        self.assertEqual(rc.read_regular_file_bounded(path, 10), b"x" * 10)
        with self.assertRaisesRegex(rc.BoundedReadError, "exceeds"):
            rc.read_regular_file_bounded(path, 9)

    def test_symlink_directory_and_missing_path_are_refused(self) -> None:
        target = self.dir / "t"
        target.write_text("x", encoding="utf-8")
        (self.dir / "link").symlink_to(target)
        for path in (self.dir / "link", self.dir, self.dir / "nope"):
            with self.assertRaises(rc.BoundedReadError, msg=str(path)):
                rc.read_regular_file_bounded(path, 100)

    def test_file_without_read_bits_is_refused(self) -> None:
        path = self.dir / "f"
        path.write_text("x", encoding="utf-8")
        path.chmod(0)
        self.addCleanup(path.chmod, 0o644)
        with self.assertRaisesRegex(rc.BoundedReadError, "readable"):
            rc.read_regular_file_bounded(path, 100)


class AppleDoubleTests(unittest.TestCase):
    def test_only_a_dot_underscore_file_with_the_magic_header_is_a_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "._real").write_bytes(rc.APPLEDOUBLE_MAGIC + b"data")
            (root / "._fake").write_bytes(b"just a hidden user file")
            (root / "plain").write_bytes(rc.APPLEDOUBLE_MAGIC)
            self.assertTrue(rc.is_appledouble_sidecar(root / "._real"))
            self.assertFalse(rc.is_appledouble_sidecar(root / "._fake"))
            self.assertFalse(rc.is_appledouble_sidecar(root / "plain"))
            self.assertFalse(rc.is_appledouble_sidecar(root / "._missing"))


class AbandonedReservationTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.run = self.root / "run"
        for name in (".tmp", "workspace", "artifact"):
            (self.run / name).mkdir(parents=True)
        self.commit = self.root / "run.commit"

    def test_bare_scaffold_without_commit_is_abandoned(self) -> None:
        self.assertTrue(rc.is_abandoned_run_reservation(self.run, self.commit))
        (self.run / "artifact" / "PROMPT.md").write_text("p", encoding="utf-8")
        self.assertTrue(rc.is_abandoned_run_reservation(self.run, self.commit))

    def test_commit_marker_makes_the_run_real(self) -> None:
        self.commit.write_bytes(b"")
        self.assertFalse(rc.is_abandoned_run_reservation(self.run, self.commit))

    def test_any_worker_content_means_it_is_not_abandoned(self) -> None:
        (self.run / "workspace" / "src.js").write_text("x", encoding="utf-8")
        self.assertFalse(rc.is_abandoned_run_reservation(self.run, self.commit))

    def test_unexpected_entry_or_extra_artifact_file_means_not_abandoned(self) -> None:
        (self.run / "notes.txt").write_text("x", encoding="utf-8")
        self.assertFalse(rc.is_abandoned_run_reservation(self.run, self.commit))
        (self.run / "notes.txt").unlink()
        (self.run / "artifact" / "index.html").write_text("x", encoding="utf-8")
        self.assertFalse(rc.is_abandoned_run_reservation(self.run, self.commit))


class IdentityTests(unittest.TestCase):
    def test_identity_key_is_slug_plus_digest_of_exact_utf8_bytes(self) -> None:
        digest = hashlib.sha256("Claude Opus 4".encode()).hexdigest()[:32]
        self.assertEqual(rc.identity_key("Claude Opus 4"), f"claude-opus-{digest}")

    def test_names_that_normalise_alike_still_get_distinct_keys(self) -> None:
        self.assertNotEqual(rc.identity_key("GPT 5"), rc.identity_key("gpt-5"))
        self.assertEqual(rc.identity_key("日本語").split("-")[0], "unnamed")

    def test_experiment_slug_rules(self) -> None:
        self.assertEqual(rc.experiment_slug("LibreOffice Writer"), "libreoffice-writer")
        self.assertEqual(rc.experiment_slug("Café — Menu!"), "cafe-menu")
        self.assertTrue(rc.experiment_slug("日本語").startswith("experiment-"))
        self.assertEqual(rc.experiment_slug("2048"), "experiment-2048")  # a pure-digit slug would read as a timestamp part
        self.assertNotEqual(rc.experiment_slug("日本語"), rc.experiment_slug("中文"))

    def test_long_slug_is_truncated_to_the_limit_with_a_digest_suffix(self) -> None:
        long_name = "word " * 40
        slug = rc.experiment_slug(long_name)
        self.assertLessEqual(len(slug), rc.EXPERIMENT_SLUG_MAX_CHARS)
        self.assertNotIn("--", slug)
        self.assertEqual(slug[-8:], hashlib.sha256(long_name.encode()).hexdigest()[:8])
        exact = "a" * rc.EXPERIMENT_SLUG_MAX_CHARS
        self.assertEqual(rc.experiment_slug(exact), exact)


class ExactChildTests(unittest.TestCase):
    def test_returns_only_the_stored_spelling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "Index.html").write_text("x", encoding="utf-8")
            self.assertIsNotNone(rc.exact_child(Path(tmp), "Index.html"))
            self.assertIsNone(rc.exact_child(Path(tmp), "index.html"))
            self.assertIsNone(rc.exact_child(Path(tmp) / "missing", "x"))


if __name__ == "__main__":
    unittest.main()
