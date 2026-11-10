"""cleanup_run_tmp deletes scratch space; it must refuse unless the run is provably finished and its own."""

from __future__ import annotations

import shutil
import unittest

import cleanup_run_tmp
from run_fixtures import OutputRoot, STATIC_INDEX, edit_json, not_required_gauntlet, run_script


class CleanupTests(OutputRoot):
    def ready_gauntlet_run(self):
        """A RUNNING run with everything cleanup requires, `.tmp/` still present."""
        run = self.prepare()
        (run / "artifact" / "index.html").write_text(STATIC_INDEX, encoding="utf-8")
        self.mark_status(run, "RUNNING")

        def fill(report: dict) -> None:
            report["artifact"]["staticDeploymentVerified"] = True
            report["qualityGauntlet"] = not_required_gauntlet()
            report["verification"] = [{"kind": "smoke", "result": "passed", "evidence": "opened"}]

        edit_json(run / "worker-report.json", fill)
        (run / ".tmp" / "scratch.txt").write_text("x", encoding="utf-8")
        return run

    def assert_refused(self, run, fragment: str) -> None:
        with self.assertRaisesRegex(cleanup_run_tmp.TemporaryCleanupError, fragment):
            cleanup_run_tmp.cleanup_run_temporary(run, True)
        self.assertTrue((run / ".tmp" / "scratch.txt").exists(), "scratch must survive a refusal")

    def test_deletes_only_tmp_and_leaves_the_handoff_alone(self) -> None:
        run = self.ready_gauntlet_run()
        self.assertEqual(cleanup_run_tmp.cleanup_run_temporary(run, True), "deleted")
        self.assertFalse((run / ".tmp").exists())
        for kept in ("artifact/PROMPT.md", "artifact/index.html", "run.json", "worker-report.json", "workspace"):
            self.assertTrue((run / kept).exists(), kept)

    def test_second_cleanup_reports_already_absent(self) -> None:
        run = self.ready_gauntlet_run()
        cleanup_run_tmp.cleanup_run_temporary(run, True)
        self.assertEqual(cleanup_run_tmp.cleanup_run_temporary(run, True), "already-absent")

    def test_refuses_without_confirmation(self) -> None:
        run = self.ready_gauntlet_run()
        with self.assertRaisesRegex(cleanup_run_tmp.TemporaryCleanupError, "--confirm-finalized"):
            cleanup_run_tmp.cleanup_run_temporary(run, False)
        self.assertTrue((run / ".tmp" / "scratch.txt").exists())

    def test_refuses_planned_or_failed_status(self) -> None:
        for status in ("PLANNED", "BLOCKED", "ERROR", "PARTIAL"):
            run = self.ready_gauntlet_run()
            self.mark_status(run, status)
            self.assert_refused(run, "must share RUNNING or OK status")

    def test_refuses_when_manifest_and_report_statuses_differ(self) -> None:
        run = self.ready_gauntlet_run()
        edit_json(run / "worker-report.json", lambda r: r.update(status="OK"))
        self.assert_refused(run, "must share RUNNING or OK")

    def test_gauntlet_requires_local_static_handoff_and_passed_evidence(self) -> None:
        run = self.ready_gauntlet_run()
        edit_json(run / "worker-report.json", lambda r: r["artifact"].update(staticDeploymentVerified=False))
        self.assert_refused(run, "static-handoff verification")
        run = self.ready_gauntlet_run()
        edit_json(run / "worker-report.json", lambda r: r.update(verification=[]))
        self.assert_refused(run, "structured passed verification evidence")

    def test_refuses_when_sealed_prompt_was_edited(self) -> None:
        run = self.ready_gauntlet_run()
        (run / "artifact" / "PROMPT.md").write_text("tampered\n", encoding="utf-8")
        self.assert_refused(run, "sealed prompt identity differs")

    def test_refuses_when_receipt_or_commit_marker_is_missing_or_disagrees(self) -> None:
        run = self.ready_gauntlet_run()
        edit_json(self.receipt_path(run), lambda d: d.update(runPath="elsewhere"))
        self.assert_refused(run, "receipt does not match")
        run = self.ready_gauntlet_run()
        (self.root / ".oneshot-provenance" / f"{run.name}.commit").unlink()
        self.assert_refused(run, "missing its coordinator receipt or commit marker")

    def test_refuses_when_worker_rewrote_identity(self) -> None:
        run = self.ready_gauntlet_run()
        edit_json(run / "run.json", lambda d: d["identity"]["model"].update(name="Other"))
        self.assert_refused(run, "identity differs from coordinator receipt")

    def test_refuses_old_run_schema_and_foreign_run_id(self) -> None:
        run = self.ready_gauntlet_run()
        edit_json(run / "run.json", lambda d: d.update(schemaVersion="3.4"))
        self.assert_refused(run, "requires run schema 3.5")
        run = self.ready_gauntlet_run()
        edit_json(run / "run.json", lambda d: d.update(runId="someone-else"))
        self.assert_refused(run, "runId matches")

    def test_refuses_a_symlinked_tmp_and_keeps_its_target(self) -> None:
        run = self.ready_gauntlet_run()
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep", encoding="utf-8")
        shutil.rmtree(run / ".tmp")
        (run / ".tmp").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(cleanup_run_tmp.TemporaryCleanupError):
            cleanup_run_tmp.cleanup_run_temporary(run, True)
        self.assertTrue((outside / "keep.txt").exists())

    def test_generation_only_run_cleans_up_to_unverified_and_rejects_verification_claims(self) -> None:
        run = self.prepare(verification="none")
        self.mark_status(run, "RUNNING")
        self.assertEqual(cleanup_run_tmp.cleanup_run_temporary(run, True), "deleted")
        run = self.prepare(verification="none", experiment="Other")
        (run / ".tmp" / "scratch.txt").write_text("x", encoding="utf-8")
        self.mark_status(run, "RUNNING")
        edit_json(run / "worker-report.json", lambda r: r.update(verification=[{"kind": "k", "result": "passed", "evidence": "e"}]))
        self.assert_refused(run, "verification \\[\\]")
        edit_json(run / "worker-report.json", lambda r: r.update(verification=[]))
        self.mark_status(run, "OK")
        self.assert_refused(run, "must share RUNNING or UNVERIFIED")

    def test_command_line_requires_the_confirmation_flag_and_prints_json(self) -> None:
        run = self.ready_gauntlet_run()
        refused = run_script("cleanup_run_tmp.py", "--run", str(run))
        self.assertNotEqual(refused.returncode, 0)
        self.assertTrue((run / ".tmp").exists())
        done = run_script("cleanup_run_tmp.py", "--run", str(run), "--confirm-finalized")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('"deleted"', done.stdout)


if __name__ == "__main__":
    unittest.main()
