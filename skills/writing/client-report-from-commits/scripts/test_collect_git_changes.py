"""Runs collect_git_changes.py against a throwaway git repo."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HELPER = Path(__file__).resolve().parent / "collect_git_changes.py"
ENV = {**os.environ, "TZ": "UTC"}


def git(repo: Path, *args: str, date: str | None = None) -> None:
    env = dict(ENV)
    if date:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{date}T12:00:00+00:00"
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


def helper(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(HELPER), *args], capture_output=True, text=True, env=ENV)


class CollectGitChangesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls._tmp.name)
        git(cls.repo, "init", "-q")
        for key, value in (("user.name", "T"), ("user.email", "t@example.com"), ("commit.gpgSign", "false")):
            git(cls.repo, "config", key, value)
        commits = [
            ("docs/legacy.md", "docs: add legacy notes", "2026-03-30"),
            ("checkout/flow.md", "feat(checkout): simplify payment journey", "2026-04-05"),
            ("reports/overview.md", "feat(reports): expand client reporting", "2026-04-06"),
            ("infra/queue.md", "chore(infra): stabilize background jobs", "2026-04-08"),
        ]
        for path, message, date in commits:
            (cls.repo / path).parent.mkdir(parents=True, exist_ok=True)
            (cls.repo / path).write_text(message + "\n")
            git(cls.repo, "add", path)
            git(cls.repo, "commit", "-q", "-m", message, date=date)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_bounded_range_selects_commits_and_scopes(self) -> None:
        result = helper("--repo", str(self.repo), "--since", "2026-04-01", "--until", "2026-04-06")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["commit_count"], 2)
        self.assertEqual({s["scope"] for s in payload["scopes"]}, {"checkout", "reports"})

    def test_relative_date_is_rejected(self) -> None:
        result = helper("--repo", str(self.repo), "--since", "this-week")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("YYYY-MM-DD", result.stderr)

    def test_missing_repo_is_reported(self) -> None:
        result = helper("--repo", str(self.repo / "missing"), "--since", "2026-04-01")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
