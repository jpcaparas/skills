import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCANNER = Path(__file__).with_name("scan_patterns.py")


def scan(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCANNER), str(root), "--json", *args], capture_output=True, text=True)


class ScanPatternsTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def test_flags_dangerous_patterns_and_fails_on_threshold(self) -> None:
        (self.root / "agent.py").write_text(
            "import subprocess\nsubprocess.run(cmd, shell=True)\neval(model_output)\nsafe = 1\n"
        )
        result = scan(self.root, "--fail-on", "high")
        self.assertEqual(2, result.returncode)
        found = {(f["id"], f["line"]) for f in json.loads(result.stdout)["findings"]}
        self.assertEqual({("shell-true", 2), ("model-output-exec", 3)}, found)

    def test_ignore_marker_and_excluded_directories_are_skipped(self) -> None:
        (self.root / "ok.py").write_text("eval(model_output)  # secure-ai-agent-scan: ignore\n")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "dep.py").write_text("eval(model_output)\n")
        result = scan(self.root, "--fail-on", "low")
        self.assertEqual(0, result.returncode)
        self.assertEqual([], json.loads(result.stdout)["findings"])


if __name__ == "__main__":
    unittest.main()
