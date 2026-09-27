#!/usr/bin/env python3
"""Exercise workflow output boundaries using disposable projects only."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


RENDERER = Path(__file__).with_name("render_setup_workflow.py")
WORKFLOW = Path(".github/workflows/copilot-setup-steps.yml")


class RendererPathTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.project = self.root / "project"
        self.project.mkdir()
        self.outside = self.root / "outside"
        self.outside.mkdir()
        self.plan = self.root / "plan.json"
        self.plan.write_text(
            json.dumps({"steps": [{"name": "Prepare", "run": "echo safe"}]}),
            encoding="utf-8",
        )

    def render(self, *, preview: bool = False) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable, str(RENDERER), "--project", str(self.project),
            "--plan", str(self.plan),
        ]
        if preview:
            command.append("--stdout")
        return subprocess.run(command, capture_output=True, text=True, timeout=10)

    def test_selected_project_root_resolves_and_preserves_previous_workflow(self) -> None:
        # macOS temporary directories have aliased parents (/var -> /private/var).
        # Exercise a selected-root alias on every platform, not an output symlink.
        project_alias = self.root / "project-alias"
        project_alias.symlink_to(self.project, target_is_directory=True)
        self.project = project_alias
        destination = self.project / WORKFLOW
        destination.parent.mkdir(parents=True)
        destination.write_text("original workflow\n", encoding="utf-8")

        result = self.render()

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(str(destination.resolve()), report["workflow_path"])
        self.assertTrue(report["changed"])
        self.assertIn('run: "echo safe"', destination.read_text(encoding="utf-8"))
        self.assertEqual(
            "original workflow\n",
            Path(report["backup_path"]).read_text(encoding="utf-8"),
        )
        second = self.render()
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertFalse(json.loads(second.stdout)["changed"])
        self.assertIsNone(json.loads(second.stdout)["backup_path"])

    def test_symlinked_output_components_cannot_write_outside_project(self) -> None:
        for relative in (Path(".github"), Path(".github/workflows"), WORKFLOW):
            with self.subTest(component=str(relative)):
                project = self.root / ("project-" + relative.name)
                project.mkdir()
                self.project = project
                link = project / relative
                link.parent.mkdir(parents=True, exist_ok=True)
                remaining = WORKFLOW.relative_to(relative)
                target = self.outside / ("target-" + relative.name)
                if remaining.parts:
                    target.mkdir()
                    sentinel = target / remaining
                    sentinel.parent.mkdir(parents=True, exist_ok=True)
                else:
                    sentinel = target
                sentinel.write_text("outside sentinel\n", encoding="utf-8")
                link.symlink_to(target, target_is_directory=bool(remaining.parts))

                result = self.render()

                self.assertNotEqual(0, result.returncode)
                self.assertIn("symlink", result.stderr.lower())
                self.assertTrue(link.is_symlink())
                self.assertEqual("outside sentinel\n", sentinel.read_text(encoding="utf-8"))
                self.assertEqual([], list(self.outside.rglob("*.bak.*")))

    def test_dangling_destination_symlink_does_not_create_its_target(self) -> None:
        destination = self.project / WORKFLOW
        destination.parent.mkdir(parents=True)
        target = self.outside / "missing.yml"
        destination.symlink_to(target)

        result = self.render()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("symlink", result.stderr.lower())
        self.assertFalse(target.exists())
        self.assertTrue(destination.is_symlink())

    def test_preview_does_not_follow_or_modify_destination_symlinks(self) -> None:
        (self.project / ".github").symlink_to(self.outside, target_is_directory=True)

        result = self.render(preview=True)

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("copilot-setup-steps:", result.stdout)
        self.assertEqual([], list(self.outside.iterdir()))

    def test_plan_cannot_select_an_absolute_or_traversing_output_path(self) -> None:
        target = self.outside / "sentinel.yml"
        target.write_text("outside sentinel\n", encoding="utf-8")
        for output_path in (str(target), "../outside/sentinel.yml"):
            with self.subTest(output_path=output_path):
                self.plan.write_text(json.dumps({
                    "workflow_path": output_path,
                    "steps": [{"name": "Prepare", "run": "echo safe"}],
                }), encoding="utf-8")

                result = self.render()

                self.assertNotEqual(0, result.returncode)
                self.assertIn("workflow_path must target", result.stderr)
                self.assertEqual("outside sentinel\n", target.read_text(encoding="utf-8"))
                self.assertEqual([], list(self.project.iterdir()))


if __name__ == "__main__":
    unittest.main()
