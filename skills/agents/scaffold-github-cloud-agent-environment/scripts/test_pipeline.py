#!/usr/bin/env python3
"""Run audit -> plan -> render -> doctor against disposable projects."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parent


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=False)


def make_project(root: Path, package: dict, lfs: bool) -> Path:
    root.mkdir()
    (root / "package.json").write_text(json.dumps(package), encoding="utf-8")
    (root / "package-lock.json").write_text("{}\n", encoding="utf-8")
    if lfs:
        (root / ".gitattributes").write_text("*.bin filter=lfs diff=lfs merge=lfs -text\n", encoding="utf-8")
    run("git", "init", "-q", str(root))
    return root


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.tmp = Path(temporary.name)

    def test_npm_lfs_project_flows_through_every_stage(self) -> None:
        project = make_project(
            self.tmp / "project",
            {"name": "fixture", "packageManager": "npm@10.8.0", "engines": {"node": "20"}, "scripts": {"test": "echo"}},
            lfs=True,
        )

        audit = run("bash", str(SCRIPTS / "audit_project.sh"), str(project))
        self.assertEqual(audit.returncode, 0, audit.stderr)
        facts = json.loads(audit.stdout)
        self.assertIn("npm", facts["package_managers"])
        self.assertIs(facts["lfs_detected"], True)

        plan_path = self.tmp / "plan.json"
        suggest = run(sys.executable, str(SCRIPTS / "suggest_plan.py"), "--project", str(project), "--output", str(plan_path))
        self.assertEqual(suggest.returncode, 0, suggest.stderr)
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        self.assertEqual(plan["questions"], [])
        self.assertIn("npm ci", [step.get("run") for step in plan["steps"]])

        render = run(sys.executable, str(SCRIPTS / "render_setup_workflow.py"), "--project", str(project), "--plan", str(plan_path))
        self.assertEqual(render.returncode, 0, render.stderr or render.stdout)
        workflow = (project / ".github" / "workflows" / "copilot-setup-steps.yml").read_text(encoding="utf-8")
        self.assertIn("copilot-setup-steps:", workflow)
        self.assertIn("lfs: true", workflow)

        doctor = run(sys.executable, str(SCRIPTS / "doctor.py"), "--project", str(project), "--symptom", "dependencies fail to install", "--json")
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertTrue(report["workflow_exists"])
        self.assertIsInstance(report["findings"], list)

    def test_renderer_refuses_plan_with_unresolved_questions(self) -> None:
        project = make_project(self.tmp / "ambiguous", {"name": "ambiguous", "scripts": {"test": "echo"}}, lfs=False)
        plan_path = self.tmp / "plan.json"
        suggest = run(sys.executable, str(SCRIPTS / "suggest_plan.py"), "--project", str(project), "--output", str(plan_path))
        self.assertEqual(suggest.returncode, 0, suggest.stderr)

        render = run(sys.executable, str(SCRIPTS / "render_setup_workflow.py"), "--project", str(project), "--plan", str(plan_path))
        self.assertNotEqual(render.returncode, 0)
        self.assertFalse((project / ".github" / "workflows" / "copilot-setup-steps.yml").exists())


if __name__ == "__main__":
    unittest.main()
