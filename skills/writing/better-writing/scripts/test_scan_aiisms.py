"""Runs the scanner's built-in safety checks and one end-to-end scan."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCANNER = Path(__file__).resolve().parent / "scan_aiisms.py"


class ScanAiismsTest(unittest.TestCase):
    def test_built_in_self_test_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCANNER), "--self-test"], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_json_scan_reports_a_formulaic_phrase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            draft = Path(tmp) / "draft.md"
            draft.write_text(
                "In today's fast-paced world, this tool plays a critical role in unlocking value.\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(SCANNER), "--format", "json", str(draft)],
                capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main()
