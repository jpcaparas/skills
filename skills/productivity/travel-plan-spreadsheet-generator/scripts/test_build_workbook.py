"""Builds the sample trip model and checks the workbook passes the shipped validators."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
EXAMPLE_MODEL = SCRIPTS / "example_trip_model.json"


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        capture_output=True,
        text=True,
        cwd=SCRIPTS,
    )


class BuildWorkbookTest(unittest.TestCase):
    def test_example_model_builds_and_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workbook = Path(tmp) / "sample.xlsx"
            build = run_script(
                "build_workbook.py",
                "--trip-model", str(EXAMPLE_MODEL),
                "--output", str(workbook),
                "--normalized-model-out", str(Path(tmp) / "normalized.json"),
            )
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            self.assertTrue(workbook.exists())

            validate = run_script(
                "validate_workbook.py", str(workbook),
                "--trip-model", str(EXAMPLE_MODEL), "--json",
            )
            self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)
            self.assertTrue(json.loads(validate.stdout)["valid"])

            render = run_script("render_check.py", str(workbook))
            self.assertEqual(render.returncode, 0, render.stdout + render.stderr)


if __name__ == "__main__":
    unittest.main()
