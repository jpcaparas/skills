"""End-to-end directional gate in real Chromium: correct A/D steering passes, inverted steering fails.

The browser is the one the pinned Playwright package selects, driven by browser_session's paused
clock, so nothing here sleeps in real time. Everything else is unit-tested per script.
"""

from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from run_fixtures import RACING_PROMPT, SKILL, OutputRoot, run_script

FIXTURES = SKILL / "evals" / "files" / "directional-controls"


class DirectionalGateTests(OutputRoot):
    def gauntlet_run_with(self, fixture: str) -> Path:
        run = self.prepare(RACING_PROMPT, "Pod Racing Game")
        self.finalize_ok(run)
        shutil.copyfile(FIXTURES / fixture / "index.html", run / "artifact" / "index.html")
        self.rebuild_index()
        return run

    def gate(self, run: Path) -> tuple[int, dict]:
        result = run_script("verify_directional_controls.py", "--run", str(run))
        return result.returncode, json.loads(result.stdout)

    def test_correct_fixture_passes_all_four_keys_and_the_validator_accepts_the_evidence(self) -> None:
        run = self.gauntlet_run_with("correct")
        code, data = self.gate(run)
        self.assertEqual((code, data["status"]), (0, "passed"))
        self.assertEqual({c["code"] for c in data["checks"]}, {"KeyA", "ArrowLeft", "KeyD", "ArrowRight"})
        self.assert_valid(self.validate())

    def test_inverted_fixture_fails_every_key_and_the_validator_rejects_the_run(self) -> None:
        run = self.gauntlet_run_with("inverted")
        code, data = self.gate(run)
        by_code = {c["code"]: c for c in data["checks"]}
        self.assertEqual((code, data["status"]), (1, "failed"))
        self.assertGreater(by_code["KeyA"]["response"], 0)
        self.assertLess(by_code["KeyD"]["response"], 0)
        self.assertTrue(all(c["passed"] is False for c in by_code.values()))
        self.assert_rejected(self.validate(), "did not pass")


if __name__ == "__main__":
    unittest.main()
