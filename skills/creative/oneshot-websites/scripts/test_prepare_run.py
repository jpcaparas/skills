"""prepare_run seals the prompt and writes the coordinator receipt every later gate trusts."""

from __future__ import annotations

import hashlib
import json
import shutil
import unittest
from pathlib import Path

import prepare_run
from run_fixtures import POSTER_PROMPT, RACING_PROMPT, OutputRoot, read_json, run_script


class SealingTests(OutputRoot):
    def test_prompt_is_sealed_byte_for_byte_and_digests_agree_everywhere(self) -> None:
        prompt = "Create a calm “museum guide” — café edition 🚀\r\nsecond line, no final newline"
        run = self.prepare(prompt, "Museum Guide")
        sealed = (run / "artifact" / "PROMPT.md").read_bytes()
        self.assertEqual(sealed, prompt.encode("utf-8"))
        digest = hashlib.sha256(sealed).hexdigest()
        self.assertEqual(read_json(run / "run.json")["prompt"]["sha256"], digest)
        receipt = read_json(self.receipt_path(run))
        self.assertEqual(receipt["prompt"], {"sha256": digest, "bytes": len(sealed)})

    def test_run_layout_names_and_initial_state(self) -> None:
        run = self.prepare(experiment="River Atlas")
        self.assertRegex(run.name, r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}-river-atlas$")
        for name in (".tmp", "workspace", "artifact"):
            self.assertTrue((run / name).is_dir(), name)
        self.assertEqual(sorted(p.name for p in (run / "artifact").iterdir()), ["PROMPT.md"])
        manifest, report = read_json(run / "run.json"), read_json(run / "worker-report.json")
        self.assertEqual((manifest["status"], report["status"]), ("PLANNED", "PLANNED"))
        self.assertEqual(manifest["identity"]["experiment"]["name"], "River Atlas")
        self.assertEqual((self.root / ".oneshot-provenance" / f"{run.name}.commit").stat().st_size, 0)

    def test_same_second_runs_get_unique_collision_suffixes(self) -> None:
        names = [self.prepare(experiment="River Atlas").name for _ in range(3)]
        self.assertEqual(len(set(names)), 3)
        self.assertTrue(all(n.split("--")[-1] in {"02", "03"} for n in names if "--" in n))

    def test_gauntlet_receipt_requires_quality_gauntlet_and_none_does_not(self) -> None:
        gauntlet = read_json(self.receipt_path(self.prepare(experiment="A")))
        none = self.prepare(experiment="B", verification="none")
        none_receipt = read_json(self.receipt_path(none))
        self.assertTrue(gauntlet["qualityGauntlet"]["required"])
        self.assertFalse(none_receipt["qualityGauntlet"]["required"])
        self.assertIsNone(read_json(none / "worker-report.json")["qualityGauntlet"])
        self.assertEqual(read_json(none / "worker-report.json")["verification"], [])


class DirectionalPreparationTests(OutputRoot):
    def test_applicable_gauntlet_run_gets_technical_prompt_outside_the_artifact(self) -> None:
        run = self.prepare(RACING_PROMPT, "Pod Racing")
        contract = read_json(run / "run.json")["interaction"]["directionalControls"]
        self.assertTrue(contract["required"])
        self.assertTrue((run / ".tmp" / "TECHNICAL_PROMPT.md").is_file())
        self.assertNotIn(b"__ONESHOT_DIRECTIONAL", (run / "artifact" / "PROMPT.md").read_bytes())
        self.assertEqual(contract, read_json(self.receipt_path(run))["directionalControls"])

    def test_generation_only_never_requires_the_gate_even_for_a_racing_game(self) -> None:
        run = self.prepare(RACING_PROMPT, "Pod Racing", verification="none")
        contract = read_json(run / "run.json")["interaction"]["directionalControls"]
        self.assertEqual((contract["required"], contract["basis"]), (False, "verification-disabled"))
        self.assertFalse((run / ".tmp" / "TECHNICAL_PROMPT.md").exists())

    def test_coordinator_can_force_the_gate_for_an_unusual_case(self) -> None:
        run = self.prepare(POSTER_PROMPT, "Poster", directional_controls="required")
        self.assertTrue(read_json(run / "run.json")["interaction"]["directionalControls"]["required"])

    def test_non_directional_site_has_no_gate(self) -> None:
        run = self.prepare()
        self.assertFalse(read_json(run / "run.json")["interaction"]["directionalControls"]["required"])
        self.assertFalse((run / ".tmp" / "TECHNICAL_PROMPT.md").exists())


class RejectionTests(OutputRoot):
    """Every rejection must happen before anything is reserved."""

    def assert_refused(self, fragment: str, **kwargs) -> None:
        with self.assertRaisesRegex(prepare_run.RunPreparationError, fragment):
            self.prepare(**kwargs)
        self.assertEqual([p for p in self.root.iterdir() if p.name != ".oneshot-provenance"] if self.root.exists() else [], [])

    def test_mojibake_prompt(self) -> None:
        self.assert_refused("mojibake", prompt="Cinnamonâ€™s desktop\n")

    def test_replacement_character_prompt(self) -> None:
        self.assert_refused("mojibake", prompt="broken \ufffd text\n")

    def test_probe_contract_in_prose(self) -> None:
        self.assert_refused("prose experience brief", prompt="Expose window.__ONESHOT_DIRECTIONAL_CONTROL_PROBE__.\n")

    def test_blank_prompt_and_blank_names(self) -> None:
        self.assert_refused("empty|blank", prompt="  \n")
        self.assert_refused("experiment must not be empty", experiment="   ")

    def test_invalid_utf8_prompt(self) -> None:
        path = self.tmp / "bad.md"
        path.write_bytes(b"caf\xe9\n")
        arguments = prepare_run.argparse.Namespace(
            output_root=self.root, model="m", harness="h", experiment="e", prompt_file=path,
            verification="gauntlet", classification="autonomous-one-shot", prior_run=None,
            directional_controls="auto",
        )
        with self.assertRaisesRegex(prepare_run.RunPreparationError, "UTF-8"):
            prepare_run.create_run(arguments)

    def test_oversized_prompt(self) -> None:
        self.assert_refused("exceeds|larger|limit", prompt="x" * (prepare_run.PROMPT_MAX_BYTES + 1))

    def test_prompt_exactly_at_limit_is_accepted(self) -> None:
        run = self.prepare(prompt="x" * prepare_run.PROMPT_MAX_BYTES)
        self.assertEqual((run / "artifact" / "PROMPT.md").stat().st_size, prepare_run.PROMPT_MAX_BYTES)

    def test_relationship_rules(self) -> None:
        self.assert_refused("must declare --prior-run", classification="rerun")
        first = self.prepare(experiment="First")
        with self.assertRaisesRegex(prepare_run.RunPreparationError, "must not declare a prior run"):
            self.prepare(experiment="Second", prior_run=first)


class PriorRunTests(OutputRoot):
    def test_valid_prior_run_is_stored_as_a_relative_name(self) -> None:
        first = self.prepare(experiment="First")
        second = self.prepare(experiment="Second", classification="curated-attempt", prior_run=first)
        self.assertEqual(read_json(second / "run.json")["priorRun"], first.name)
        self.assertEqual(read_json(self.receipt_path(second))["priorRun"], first.name)

    def test_prior_run_outside_root_or_nested_is_refused(self) -> None:
        first = self.prepare(experiment="First")
        outside = self.tmp / "elsewhere"
        shutil.copytree(first, outside)
        for bad in (outside, first / "artifact", self.root):
            with self.assertRaises(prepare_run.RunPreparationError, msg=str(bad)):
                self.prepare(experiment="Second", classification="rerun", prior_run=bad)

    def test_wrong_case_prior_run_is_refused(self) -> None:
        first = self.prepare(experiment="First")
        with self.assertRaisesRegex(prepare_run.RunPreparationError, "exact casing|within output root|could not be mapped"):
            self.prepare(experiment="Second", classification="rerun", prior_run=self.root / first.name.upper())

    def test_prior_run_that_never_committed_is_refused(self) -> None:
        first = self.prepare(experiment="First")
        (self.root / ".oneshot-provenance" / f"{first.name}.commit").unlink()
        with self.assertRaisesRegex(prepare_run.RunPreparationError, "missing its provenance commit marker"):
            self.prepare(experiment="Second", classification="rerun", prior_run=first)

    def test_prior_run_whose_receipt_disagrees_with_its_manifest_is_refused(self) -> None:
        first = self.prepare(experiment="First")
        self.receipt_path(first).write_text(json.dumps({**read_json(self.receipt_path(first)), "runId": "other"}), encoding="utf-8")
        with self.assertRaisesRegex(prepare_run.RunPreparationError, "does not match the prior run"):
            self.prepare(experiment="Second", classification="rerun", prior_run=first)

    def test_symlinked_prior_run_is_refused(self) -> None:
        first = self.prepare(experiment="First")
        link = self.root / "2026-01-01-00-00-00-link"
        link.symlink_to(first, target_is_directory=True)
        with self.assertRaisesRegex(prepare_run.RunPreparationError, "symbolic links"):
            self.prepare(experiment="Second", classification="rerun", prior_run=link)


class CommandLineTests(OutputRoot):
    def run_cli(self, *extra: str):
        return run_script(
            "prepare_run.py", "--output-root", str(self.root), "--model", "M", "--harness", "H",
            "--experiment", "Poster", "--prompt-file", str(self.write_prompt(POSTER_PROMPT)), *extra,
        )

    def test_verification_choice_is_mandatory(self) -> None:
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("--verification", result.stderr)
        self.assertFalse(self.root.exists())

    def test_success_prints_the_machine_readable_summary(self) -> None:
        result = self.run_cli("--verification", "none")
        self.assertEqual(result.returncode, 0, result.stderr)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["verificationMode"], "none")
        self.assertFalse(summary["directionalControlsRequired"])
        self.assertIsNone(summary["technicalPromptPath"])
        self.assertTrue(summary["coordinatorMonitoringRequired"])
        self.assertTrue(Path(summary["runDirectory"]).is_dir())

    def test_failure_exits_two_with_a_message_and_empty_stdout(self) -> None:
        self.write_prompt("Cinnamonâ€™s desktop\n")
        result = run_script(
            "prepare_run.py", "--output-root", str(self.root), "--model", "M", "--harness", "H",
            "--experiment", "E", "--prompt-file", str(self.tmp / "prompt.md"), "--verification", "gauntlet",
        )
        self.assertEqual((result.returncode, result.stdout), (2, ""))
        self.assertIn("mojibake", result.stderr)


if __name__ == "__main__":
    unittest.main()
