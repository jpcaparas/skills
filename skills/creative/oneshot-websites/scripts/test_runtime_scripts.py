"""Offline tests for the coordinator scripts, including the Playwright directional-controls gate.

The gate runs against the pinned Playwright Chromium with browser_session's paused clock,
so nothing here sleeps in real time.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from runtime_contract import find_likely_mojibake

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
FIXTURES = SKILL / "evals" / "files" / "directional-controls"

RACING_PROMPT = (
    "Create a browser racing game with a controllable vehicle, steering, WASD, and arrow keys. "
    "A with ArrowLeft must steer left, while D with ArrowRight must steer right.\n"
)


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args], capture_output=True, text=True, check=False
    )


def mark_status(run_path: Path, status: str) -> None:
    for name in ("run.json", "worker-report.json"):
        path = run_path / name
        data = json.loads(path.read_text(encoding="utf-8"))
        data["status"] = status
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def make_verified_static_export(run_path: Path) -> None:
    """Give a RUNNING run a passed static-handoff report so it can be finalized to OK."""
    (run_path / "artifact" / "index.html").write_text(
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>Export</title></head>"
        "<body>Built static export</body></html>\n",
        encoding="utf-8",
    )
    mark_status(run_path, "RUNNING")
    report_path = run_path / "worker-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["temporary"]["routingApplied"] = True
    report["artifact"]["staticDeploymentVerified"] = True
    report["qualityGauntlet"] = {
        "applicability": "not-required",
        "notRequiredReason": "Structural static-handoff fixture.",
        "bar": None,
        "referenceProvenance": [],
        "barValidation": {"result": None, "evidence": None},
        "barRevisions": [],
        "freshCriticAvailable": None,
        "rounds": [],
        "integrationPass": {"required": False, "result": "not-required", "evidence": "Single owner."},
        "fallbackEvidence": None,
        "stopReason": "not-required",
    }
    report["verification"] = [
        {"kind": "static-browser-smoke", "result": "passed", "evidence": "Opened the built root entrypoint"}
    ]
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


class TemporaryRoot(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="oneshot-test-")
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)

    def prepare(self, prompt: str, experiment: str, *extra: str, root: Path | None = None) -> subprocess.CompletedProcess[str]:
        prompt_file = self.tmp / "prompt.md"
        prompt_file.write_text(prompt, encoding="utf-8")
        return run_script(
            "prepare_run.py",
            "--output-root", str(root or self.tmp / "runs"),
            "--model", "Test Model",
            "--harness", "Test Harness",
            "--experiment", experiment,
            "--prompt-file", str(prompt_file),
            *extra,
        )

    def prepared_run(self, prompt: str, experiment: str, *extra: str) -> Path:
        result = self.prepare(prompt, experiment, *extra)
        self.assertEqual(result.returncode, 0, result.stderr)
        return Path(json.loads(result.stdout)["runDirectory"])

    def rebuild_index(self, root: Path) -> None:
        result = run_script("build_catalog_index.py", "--root", str(root), "--out", str(root / "index.html"))
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


class ListPromptsTests(unittest.TestCase):
    def test_unfiltered_listing_shows_every_prompt_once_without_internal_guidance(self) -> None:
        catalogue = json.loads((SKILL / "assets" / "prompt-catalogue.json").read_text(encoding="utf-8"))
        result = run_script("list_prompts.py")
        self.assertEqual(result.returncode, 0, result.stderr)
        for prompt in catalogue["prompts"]:
            self.assertEqual(result.stdout.count(f"`{prompt['id']}`"), 1, prompt["id"])
        self.assertIn(f"{len(catalogue['prompts'])} prompt(s), grouped by namespace", result.stdout)
        self.assertNotIn(catalogue["experienceDirection"], result.stdout)
        self.assertNotIn(catalogue["completionMandate"], result.stdout)


class MojibakeTests(unittest.TestCase):
    def test_valid_unicode_passes_and_corruption_is_flagged(self) -> None:
        for sample in ("— – ‘single’ “double” … café naïve", "日本語 العربية 🚀"):
            self.assertIsNone(find_likely_mojibake(sample), sample)
        for sample in ("â€”", "cafÃ©", "ðŸš€", "replacement \ufffd", "stray control \u0081"):
            self.assertIsNotNone(find_likely_mojibake(sample), sample)


class PrepareRunTests(TemporaryRoot):
    def test_prompt_is_sealed_byte_for_byte_in_a_flat_run(self) -> None:
        prompt = "Create a calm “museum guide” — café edition 🚀\n"
        run_path = self.prepared_run(prompt, "Museum Guide")
        self.assertEqual((run_path / "artifact" / "PROMPT.md").read_bytes(), prompt.encode("utf-8"))
        self.assertRegex(run_path.name, r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-museum-guide")
        self.assertTrue((run_path / ".tmp").is_dir())
        self.assertEqual(json.loads((run_path / "run.json").read_text())["status"], "PLANNED")

    def test_same_second_reservations_get_distinct_suffixed_runs(self) -> None:
        names = {self.prepared_run("Make a river atlas.\n", "River Atlas").name for _ in range(3)}
        self.assertEqual(len(names), 3)

    def test_corrupted_prompt_is_rejected_before_reserving_anything(self) -> None:
        root = self.tmp / "runs"
        result = self.prepare("Cinnamonâ€™s desktop\n", "Corrupt", root=root)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(root.exists())

    def test_internal_probe_name_in_prompt_prose_is_rejected(self) -> None:
        root = self.tmp / "runs"
        result = self.prepare(
            "Create a browser racing game. Expose window.__ONESHOT_DIRECTIONAL_CONTROL_PROBE__.\n",
            "Leaked", root=root,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must remain a prose experience brief", result.stderr)
        self.assertFalse(root.exists())

    def test_directional_game_gets_transient_technical_prompt_outside_artifact(self) -> None:
        run_path = self.prepared_run(RACING_PROMPT, "Pod Racing Game", "--verification", "gauntlet")
        manifest = json.loads((run_path / "run.json").read_text())
        contract = manifest["interaction"]["directionalControls"]
        self.assertTrue(contract["required"])
        self.assertTrue((run_path / ".tmp" / "TECHNICAL_PROMPT.md").is_file())
        self.assertNotIn(b"__ONESHOT_DIRECTIONAL_CONTROL_PROBE__", (run_path / "artifact" / "PROMPT.md").read_bytes())

    def test_generation_only_mode_creates_no_directional_contract(self) -> None:
        run_path = self.prepared_run(RACING_PROMPT, "Pod Racing Game", "--verification", "none")
        manifest = json.loads((run_path / "run.json").read_text())
        self.assertEqual(manifest["verificationMode"], "none")
        self.assertFalse((run_path / ".tmp" / "TECHNICAL_PROMPT.md").exists())

    def test_non_directional_site_needs_no_directional_contract(self) -> None:
        run_path = self.prepared_run("Create a quiet typographic poster site.\n", "Poster", "--verification", "gauntlet")
        manifest = json.loads((run_path / "run.json").read_text())
        self.assertFalse(manifest["interaction"]["directionalControls"]["required"])


class CleanupTests(TemporaryRoot):
    def test_cleanup_requires_confirmation_and_removes_only_run_tmp(self) -> None:
        run_path = self.prepared_run("Create a poster site.\n", "Poster", "--verification", "none")
        mark_status(run_path, "RUNNING")
        (run_path / ".tmp" / "scratch.txt").write_text("x", encoding="utf-8")
        refused = run_script("cleanup_run_tmp.py", "--run", str(run_path))
        self.assertNotEqual(refused.returncode, 0)
        self.assertTrue((run_path / ".tmp" / "scratch.txt").exists())
        done = run_script("cleanup_run_tmp.py", "--run", str(run_path), "--confirm-finalized")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertFalse((run_path / ".tmp").exists())
        self.assertTrue((run_path / "artifact" / "PROMPT.md").is_file())

    def test_cleanup_refuses_a_symlinked_tmp(self) -> None:
        run_path = self.prepared_run("Create a poster site.\n", "Poster", "--verification", "none")
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep", encoding="utf-8")
        shutil.rmtree(run_path / ".tmp")
        (run_path / ".tmp").symlink_to(outside, target_is_directory=True)
        result = run_script("cleanup_run_tmp.py", "--run", str(run_path), "--confirm-finalized")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((outside / "keep.txt").exists())


class DirectionalGateTests(TemporaryRoot):
    """Real Chromium: the gate must accept correct A/D steering and reject the inverted fixture."""

    def gauntlet_run_with(self, fixture: str) -> Path:
        run_path = self.prepared_run(RACING_PROMPT, "Pod Racing Game", "--verification", "gauntlet")
        make_verified_static_export(run_path)
        cleaned = run_script("cleanup_run_tmp.py", "--run", str(run_path), "--confirm-finalized")
        self.assertEqual(cleaned.returncode, 0, cleaned.stderr)
        mark_status(run_path, "OK")
        shutil.copyfile(FIXTURES / fixture / "index.html", run_path / "artifact" / "index.html")
        self.rebuild_index(run_path.parent)
        return run_path

    def gate(self, run_path: Path) -> tuple[int, dict]:
        result = run_script("verify_directional_controls.py", "--run", str(run_path))
        return result.returncode, json.loads(result.stdout)

    def test_correct_fixture_passes_all_four_keys(self) -> None:
        code, data = self.gate(self.gauntlet_run_with("correct"))
        self.assertEqual((code, data["status"]), (0, "passed"))
        self.assertEqual({c["code"] for c in data["checks"]}, {"KeyA", "ArrowLeft", "KeyD", "ArrowRight"})

    def test_inverted_fixture_fails_every_key(self) -> None:
        code, data = self.gate(self.gauntlet_run_with("inverted"))
        by_code = {c["code"]: c for c in data["checks"]}
        self.assertEqual((code, data["status"]), (1, "failed"))
        self.assertGreater(by_code["KeyA"]["response"], 0)
        self.assertLess(by_code["KeyD"]["response"], 0)
        self.assertTrue(all(c["passed"] is False for c in by_code.values()))


if __name__ == "__main__":
    unittest.main()
