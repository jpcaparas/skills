"""The gate's decision logic and evidence file, with the browser stubbed out.

The real-Chromium accept and reject cases live in test_runtime_scripts.py.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import unittest
from pathlib import Path
from unittest import mock

import directional_controls as dc
import verify_directional_controls as vdc
from run_fixtures import RACING_PROMPT, OutputRoot, read_json


def checks(**responses: float) -> list[dict]:
    expected = {"KeyA": "left", "ArrowLeft": "left", "KeyD": "right", "ArrowRight": "right"}
    values = {"KeyA": -1.0, "ArrowLeft": -1.0, "KeyD": 1.0, "ArrowRight": 1.0, **responses}
    return [
        {
            "code": code, "expected": side, "frame": "ship", "measurement": "position",
            "response": values[code], "passed": dc.response_matches_direction(values[code], side),
        }
        for code, side in expected.items()
    ]


BROWSER = vdc.BrowserInfo(Path("/fake/chrome"), "chrome", "Chromium 1.0")


class VerifyDecisionTests(OutputRoot):
    def racing_run(self, status: str = "OK") -> Path:
        run = self.prepare(RACING_PROMPT, "Pod Racing")
        if status == "OK":
            self.finalize_ok(run)
        return run

    def verify(self, run: Path, outcome=None, error: Exception | None = None):
        arguments = argparse.Namespace(run=run, browser=None, hold_ms=400)
        with mock.patch.object(vdc, "resolve_browser", return_value=BROWSER), mock.patch.object(
            vdc, "exercise_browser", return_value=outcome if outcome is not None else checks(), side_effect=error
        ):
            return vdc.verify(arguments)

    def test_passing_checks_write_evidence_bound_to_the_artifact_and_pass_validation(self) -> None:
        run = self.racing_run()
        evidence, path = self.verify(run)
        self.assertTrue(evidence["passed"])
        digest = dc.artifact_tree_digest(run / "artifact")
        self.assertEqual(evidence["artifact"]["sha256"], digest.sha256)
        self.assertEqual(read_json(path), evidence)
        self.assertEqual(path, self.root.resolve() / ".oneshot-provenance" / f"{run.name}.directional-controls.json")
        self.assert_valid(self.validate())  # the validator accepts the evidence this script writes

    def test_one_wrong_key_fails_the_gate_and_names_it(self) -> None:
        run = self.racing_run()
        evidence, _ = self.verify(run, checks(KeyD=-0.5))
        self.assertFalse(evidence["passed"])
        self.assertIn("KeyD observed -0.5", evidence["error"])
        self.assertNotIn("KeyA", evidence["error"])

    def test_missing_check_cannot_pass(self) -> None:
        run = self.racing_run()
        evidence, _ = self.verify(run, checks()[:3])
        self.assertFalse(evidence["passed"])

    def test_browser_failures_are_recorded_as_failed_evidence_not_crashes(self) -> None:
        for failure in (TimeoutError(), vdc.VerificationError("probe missing"), dc.DirectionalControlError("bad sample")):
            run = self.racing_run()
            evidence, path = self.verify(run, error=failure)
            self.assertFalse(evidence["passed"])
            self.assertTrue(evidence["error"], failure)
            self.assertTrue(path.is_file())

    def test_failed_evidence_blocks_ok_in_the_validator(self) -> None:
        run = self.racing_run()
        self.verify(run, checks(KeyA=2.0))
        self.assert_rejected(self.validate(), "directional-control browser verification did not pass")

    def test_refuses_runs_that_are_not_finalized_ok(self) -> None:
        run = self.racing_run(status="PLANNED")
        with self.assertRaisesRegex(vdc.VerificationError, "finalized run with status OK"):
            self.verify(run)

    def test_generation_only_runs_are_never_browser_verified(self) -> None:
        run = self.prepare(RACING_PROMPT, "Pod Racing", verification="none")
        with self.assertRaisesRegex(vdc.VerificationError, "forbids browser verification"):
            self.verify(run)

    def test_non_directional_run_reports_not_required_and_writes_nothing(self) -> None:
        run = self.prepare()
        result, path = self.verify(run)
        self.assertEqual(result["status"], "not-required")
        self.assertIsNone(path)
        self.assertEqual(list((self.root / ".oneshot-provenance").glob("*.directional-controls.json")), [])

    def test_run_contract_that_differs_from_receipt_is_refused(self) -> None:
        run = self.racing_run()
        manifest = read_json(run / "run.json")
        manifest["interaction"]["directionalControls"]["required"] = False
        (run / "run.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(vdc.VerificationError, "differs from its coordinator receipt"):
            self.verify(run)

    def test_main_exit_codes(self) -> None:
        run = self.racing_run()
        def main_with(outcome) -> tuple[int, dict]:
            out = io.StringIO()
            with mock.patch.object(vdc, "resolve_browser", return_value=BROWSER), mock.patch.object(
                vdc, "exercise_browser", return_value=outcome
            ), contextlib.redirect_stdout(out):
                code = vdc.main(["--run", str(run)])
            return code, json.loads(out.getvalue())
        self.assertEqual(main_with(checks())[0], 0)
        code, summary = main_with(checks(ArrowLeft=1.0))
        self.assertEqual((code, summary["status"]), (1, "failed"))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(vdc.main(["--run", str(self.tmp / "missing")]), 2)


class EvidenceFileTests(OutputRoot):
    def test_write_is_atomic_and_leaves_no_temp_files(self) -> None:
        target = self.tmp / "evidence.json"
        vdc.write_evidence(target, {"a": "é"})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"a": "é"})
        vdc.write_evidence(target, {"a": 2})
        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"a": 2})
        self.assertEqual([p.name for p in self.tmp.iterdir()], ["evidence.json"])

    def test_evidence_path_must_match_the_receipt_exactly(self) -> None:
        provenance = self.root / ".oneshot-provenance"
        provenance.mkdir(parents=True)
        good = {"evidencePath": ".oneshot-provenance/r1.directional-controls.json"}
        self.assertEqual(vdc.evidence_path(self.root, good, "r1"), self.root / good["evidencePath"])
        for bad in ({"evidencePath": "../x.json"}, {"evidencePath": None}, {}):
            with self.assertRaises(vdc.VerificationError):
                vdc.evidence_path(self.root, bad, "r1")

    def test_pass_requires_all_four_checks_and_no_error(self) -> None:
        digest = dc.ArtifactTreeDigest("0" * 64, 1, 1)
        def passed(check_list, error=None) -> bool:
            return vdc.verification_evidence("r", digest, BROWSER, 400, check_list, error)["passed"]
        self.assertTrue(passed(checks()))
        self.assertFalse(passed(checks()[:3]))
        self.assertFalse(passed(checks(), error="boom"))
        self.assertFalse(passed(checks(KeyD=-1.0)))


class ArgumentTests(unittest.TestCase):
    def test_hold_duration_bounds(self) -> None:
        for value, ok in (("99", False), ("100", True), ("5000", True), ("5001", False)):
            with contextlib.redirect_stderr(io.StringIO()):
                if ok:
                    self.assertEqual(vdc.parse_arguments(["--run", "r", "--hold-ms", value]).hold_ms, int(value))
                else:
                    with self.assertRaises(SystemExit):
                        vdc.parse_arguments(["--run", "r", "--hold-ms", value])

    def test_explicit_missing_browser_is_an_error_even_if_a_default_exists(self) -> None:
        with self.assertRaisesRegex(vdc.VerificationError, "browser unavailable"):
            vdc.resolve_browser(Path("/nonexistent/chrome"))

    def test_non_executable_browser_is_rejected(self) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile() as handle:
            with self.assertRaisesRegex(vdc.VerificationError, "executable regular file"):
                vdc.resolve_browser(Path(handle.name))


if __name__ == "__main__":
    unittest.main()
