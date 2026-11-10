"""Runs repo_readme_probe.py against a small fixture repository."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROBE = Path(__file__).resolve().parent / "repo_readme_probe.py"


class ProbeTest(unittest.TestCase):
    def test_reports_package_manager_scripts_and_env_example(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(
                json.dumps({"scripts": {"dev": "vite", "check": "npm test", "build": "vite build"}})
            )
            (root / "pnpm-lock.yaml").write_text("lockfileVersion: '9.0'\n")
            (root / ".env.example").write_text("DATABASE_URL=\n")
            (root / "README.md").write_text("# Fixture\n\n## Quickstart\n")
            result = subprocess.run(
                [sys.executable, str(PROBE), str(root)], capture_output=True, text=True
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["package_manager"], "pnpm")
        self.assertIn("package.json", data["manifests"])
        scripts = data["package_scripts"]["package.json"]
        self.assertTrue({"dev", "check"} <= set(scripts))
        self.assertIn(".env.example", data["config_examples"])


if __name__ == "__main__":
    unittest.main()
