"""The directional contract: which prompts need the A/D gate, and what counts as left or right."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import directional_controls as dc


def infer(experiment: str, prompt: str, force: bool = False) -> dc.DirectionalControlRequirement:
    return dc.infer_directional_control_requirement(experiment, prompt, force)


class ApplicabilityTests(unittest.TestCase):
    def test_games_with_steering_or_movement_need_the_gate(self) -> None:
        for prompt in (
            "A browser racing game with steering.",
            "A first-person shooter game with strafing.",
            "A 3D flight simulator you can fly.",
            "A platformer game where you walk and jump.",
            "An interactive 3D scene you orbit with WASD.",
        ):
            self.assertTrue(infer("x", prompt).required, prompt)

    def test_non_interactive_or_non_directional_sites_do_not(self) -> None:
        for prompt in (
            "A quiet typographic poster site.",
            "A chess board with drag and drop.",
            "An ordinary analytics dashboard with charts.",
            "A rotating product model viewer.",
            "A game of memory cards you click.",
        ):
            self.assertFalse(infer("x", prompt).required, prompt)

    def test_passive_3d_without_directional_controls_is_exempt_but_a_game_is_not(self) -> None:
        passive = "A passive 3D gallery of orbiting planets with no camera controls."
        self.assertFalse(infer("x", passive).required)
        self.assertTrue(infer("x", "A passive game with no steering, but arrow keys move the cursor.").required)

    def test_experiment_name_alone_can_supply_the_signal(self) -> None:
        self.assertTrue(infer("Pod Racing Game", "Make it beautiful, with steering.").required)

    def test_force_overrides_everything_and_is_recorded_as_basis(self) -> None:
        result = infer("Poster", "A poster.", force=True)
        self.assertEqual((result.required, result.basis), (True, "coordinator-required"))
        self.assertIn("coordinator-required", result.signals)

    def test_word_boundaries_prevent_false_positives(self) -> None:
        self.assertFalse(infer("x", "A gamesmanship essay about transformational drive-less design.").required)


class ContractShapeTests(unittest.TestCase):
    def test_required_contract_names_evidence_and_technical_prompt_for_its_run(self) -> None:
        contract = dc.directional_control_contract(infer("x", "A racing game with steering."), "run-1")
        self.assertEqual(contract["evidencePath"], ".oneshot-provenance/run-1.directional-controls.json")
        self.assertEqual(contract["technicalPrompt"]["path"], ".tmp/TECHNICAL_PROMPT.md")
        self.assertTrue(contract["required"])

    def test_not_required_contract_has_neither(self) -> None:
        contract = dc.directional_control_contract(infer("x", "A poster."), "run-1")
        self.assertIsNone(contract["evidencePath"])
        self.assertIsNone(contract["technicalPrompt"])


class PromptLeakTests(unittest.TestCase):
    def test_each_internal_marker_is_rejected_case_insensitively(self) -> None:
        for marker in (
            "window.__ONESHOT_DIRECTIONAL_CONTROL_PROBE__",
            "?oneshot-directional-probe=1",
            "OneshotDirectionalControlProbe",
            "directionalcontrolsample",
        ):
            with self.assertRaises(dc.DirectionalControlError, msg=marker):
                dc.reject_internal_directional_contract_in_prompt(f"Brief. {marker} end")

    def test_ordinary_prose_about_controls_is_fine(self) -> None:
        dc.reject_internal_directional_contract_in_prompt("A with ArrowLeft steers left; D with ArrowRight right.")


class TechnicalPromptTests(unittest.TestCase):
    def test_shipped_contract_document_satisfies_its_own_checker(self) -> None:
        reference = Path(__file__).resolve().parents[1] / "references" / "directional-controls.md"
        dc.validate_directional_technical_prompt_contract(reference.read_text(encoding="utf-8"))

    def test_each_missing_requirement_is_named(self) -> None:
        reference = (Path(__file__).resolve().parents[1] / "references" / "directional-controls.md").read_text(encoding="utf-8")
        stripped = reference.replace(dc.DIRECTIONAL_CONTROL_PROBE_GLOBAL, "REDACTED")
        with self.assertRaisesRegex(dc.DirectionalControlError, "probe global"):
            dc.validate_directional_technical_prompt_contract(stripped)
        with self.assertRaisesRegex(dc.DirectionalControlError, "query gate"):
            dc.validate_directional_technical_prompt_contract(reference.replace("oneshot-directional-probe=1", "x"))


def sample(position, forward=(0, 1), right=(1, 0), measurement="position", frame="ship") -> dict:
    return {"frame": frame, "measurement": measurement, "position": position, "forward": forward, "right": right}


class SampleParsingTests(unittest.TestCase):
    def test_valid_2d_and_3d_samples_parse(self) -> None:
        self.assertEqual(dc.parse_directional_sample(sample([0, 0])).frame, "ship")
        self.assertEqual(len(dc.parse_directional_sample(sample([0, 0, 0], [0, 0, 1], [1, 0, 0])).position), 3)

    def test_each_malformed_shape_is_rejected(self) -> None:
        bad_samples = [
            "text",
            sample([0, 0], frame=" "),
            sample([0, 0], measurement="speed"),
            sample([0]),  # 1D
            sample([0, 0, 0, 0]),
            sample([0, "x"]),
            sample([0, True]),
            sample([0, float("nan")]),
            sample([0, float("inf")]),
            sample([0, 0], forward=(0, 0)),  # zero basis vector
            sample([0, 0], right=(0, 0)),
            sample([0, 0, 0]),  # 3D position with 2D basis
            sample("ab"),
        ]
        for value in bad_samples:
            with self.assertRaises(dc.DirectionalControlError, msg=repr(value)):
                dc.parse_directional_sample(value)


class ResponseTests(unittest.TestCase):
    def response(self, before: dict, after: dict) -> float:
        return dc.directional_response(dc.parse_directional_sample(before), dc.parse_directional_sample(after)).value

    def test_position_response_is_the_displacement_along_the_initial_right_vector(self) -> None:
        # Facing +y with right = +x: moving to x=-3 is a leftward response of -3.
        self.assertEqual(self.response(sample([5, 5]), sample([2, 9])), -3)

    def test_rotated_frame_flips_which_world_axis_is_right(self) -> None:
        # Right basis is world -x (the player is rotated 180 degrees): moving +x is leftward.
        before = sample([0, 0], forward=(0, -1), right=(-1, 0))
        self.assertEqual(self.response(before, sample([4, 0], forward=(0, -1), right=(-1, 0))), -4)

    def test_non_unit_basis_is_normalised(self) -> None:
        self.assertAlmostEqual(self.response(sample([0, 0], right=(10, 0)), sample([2, 0], right=(10, 0))), 2)

    def test_heading_response_measures_forward_swinging_toward_right(self) -> None:
        before = sample([0, 0], forward=(0, 1), measurement="heading")
        left = sample([0, 0], forward=(-0.6, 0.8), measurement="heading")
        right = sample([0, 0], forward=(0.6, 0.8), measurement="heading")
        self.assertAlmostEqual(self.response(before, left), -0.6)
        self.assertAlmostEqual(self.response(before, right), 0.6)

    def test_height_changes_do_not_count_as_left_or_right(self) -> None:
        before = sample([0, 0, 0], [0, 0, 1], [1, 0, 0])
        after = sample([0, 7, 0], [0, 0, 1], [1, 0, 0])
        self.assertEqual(self.response(before, after), 0)

    def test_changing_frame_measurement_or_dimension_between_samples_is_an_error(self) -> None:
        base = dc.parse_directional_sample(sample([0, 0]))
        for other in (
            sample([0, 0], frame="camera"),
            sample([0, 0], measurement="heading"),
            sample([0, 0, 0], [0, 0, 1], [1, 0, 0]),
        ):
            with self.assertRaises(dc.DirectionalControlError):
                dc.directional_response(base, dc.parse_directional_sample(other))

    def test_sign_threshold_is_strict_at_epsilon(self) -> None:
        eps = dc.DIRECTIONAL_RESPONSE_EPSILON
        self.assertTrue(dc.response_matches_direction(-2 * eps, "left"))
        self.assertTrue(dc.response_matches_direction(2 * eps, "right"))
        self.assertFalse(dc.response_matches_direction(-eps, "left"))
        self.assertFalse(dc.response_matches_direction(eps, "right"))
        self.assertFalse(dc.response_matches_direction(0.5, "left"))
        self.assertFalse(dc.response_matches_direction(-0.5, "right"))
        with self.assertRaises(dc.DirectionalControlError):
            dc.response_matches_direction(1.0, "up")


class ArtifactDigestTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "artifact"
        (self.root / "sub").mkdir(parents=True)
        (self.root / "index.html").write_text("a", encoding="utf-8")
        (self.root / "sub" / "x.js").write_text("bb", encoding="utf-8")

    def test_counts_files_and_bytes_and_is_stable(self) -> None:
        first = dc.artifact_tree_digest(self.root)
        self.assertEqual((first.files, first.bytes), (2, 3))
        self.assertEqual(first, dc.artifact_tree_digest(self.root))

    def test_any_content_rename_or_addition_changes_the_digest(self) -> None:
        original = dc.artifact_tree_digest(self.root).sha256
        (self.root / "index.html").write_text("c", encoding="utf-8")  # same size, new bytes
        changed = dc.artifact_tree_digest(self.root).sha256
        self.assertNotEqual(original, changed)
        (self.root / "sub" / "x.js").rename(self.root / "sub" / "y.js")
        renamed = dc.artifact_tree_digest(self.root).sha256
        self.assertNotIn(renamed, (original, changed))
        (self.root / "new.txt").write_text("", encoding="utf-8")
        self.assertNotIn(dc.artifact_tree_digest(self.root).sha256, (original, changed, renamed))

    def test_content_moved_between_files_is_not_confused_by_concatenation(self) -> None:
        (self.root / "index.html").write_text("ab", encoding="utf-8")
        (self.root / "sub" / "x.js").write_text("b", encoding="utf-8")
        moved = dc.artifact_tree_digest(self.root).sha256
        (self.root / "index.html").write_text("a", encoding="utf-8")
        (self.root / "sub" / "x.js").write_text("bb", encoding="utf-8")
        self.assertNotEqual(moved, dc.artifact_tree_digest(self.root).sha256)

    def test_symlinks_and_limits_are_refused(self) -> None:
        (self.root / "link").symlink_to(self.root / "index.html")
        with self.assertRaises(dc.DirectionalControlError):
            dc.artifact_tree_digest(self.root)
        (self.root / "link").unlink()
        with self.assertRaisesRegex(dc.DirectionalControlError, "1-file"):
            dc.artifact_tree_digest(self.root, max_files=1)
        with self.assertRaisesRegex(dc.DirectionalControlError, "1-byte"):
            dc.artifact_tree_digest(self.root, max_file_bytes=1)
        with self.assertRaisesRegex(dc.DirectionalControlError, "2-byte verification limit"):
            dc.artifact_tree_digest(self.root, max_total_bytes=2)
        dc.artifact_tree_digest(self.root, max_files=2, max_file_bytes=2, max_total_bytes=3)


if __name__ == "__main__":
    unittest.main()
