#!/usr/bin/env python3
"""Behaviour of the shared agent stop gate, run against throwaway Git repositories."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

STOP_SCRIPT = Path(__file__).resolve().parent / "agent-stop-checks.sh"

# Stands in for validate-all-skills.sh. It records each run outside the
# worktree, so recording never changes whether the tree is clean.
VALIDATOR_STUB = """\
#!/usr/bin/env bash
printf '%s\\n' "${SKILLS_VALIDATE_ALLOW_UNTRACKED_SKILL_WORKTREE:-unset}" >>"$STUB_RUNS"
for line in $(seq 1 "$STUB_LINES"); do echo "validator line $line"; done
exit "$STUB_EXIT"
"""


class StopGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.repo = self.root / "repo"
        self.runs = self.root / "validator-runs"
        self.logs = self.root / "tmp"
        self.logs.mkdir()
        self.env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_SYSTEM": os.devnull,
            "GIT_AUTHOR_NAME": "Stop Gate",
            "GIT_AUTHOR_EMAIL": "stop-gate@example.invalid",
            "GIT_COMMITTER_NAME": "Stop Gate",
            "GIT_COMMITTER_EMAIL": "stop-gate@example.invalid",
            "TMPDIR": str(self.logs),
            "STUB_RUNS": str(self.runs),
        }

        scripts = self.repo / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy(STOP_SCRIPT, scripts / STOP_SCRIPT.name)
        (scripts / "validate-all-skills.sh").write_text(VALIDATOR_STUB)
        self.git("init", "--quiet", "--initial-branch=main")
        self.commit_everything("baseline")

    def git(self, *arguments: str) -> None:
        subprocess.run(
            ["git", *arguments],
            cwd=self.repo,
            env=self.env,
            check=True,
            capture_output=True,
        )

    def commit_everything(self, message: str) -> None:
        self.git("add", "--all")
        self.git("commit", "--quiet", f"--message={message}")

    def push_to_upstream(self) -> None:
        remote = self.root / "remote.git"
        subprocess.run(
            ["git", "init", "--quiet", "--bare", str(remote)],
            env=self.env,
            check=True,
            capture_output=True,
        )
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "--quiet", "--set-upstream", "origin", "main")

    def leave_uncommitted_work(self) -> None:
        (self.repo / "work-in-progress.md").write_text("draft\n")

    def stop(
        self,
        harness: str,
        *,
        event: str = "",
        validator_exit: int = 0,
        validator_lines: int = 3,
    ) -> subprocess.CompletedProcess[str]:
        # Run from outside the repository: harnesses do not promise a cwd.
        return subprocess.run(
            ["bash", str(self.repo / "scripts" / STOP_SCRIPT.name), harness],
            cwd=self.root,
            env={
                **self.env,
                "STUB_EXIT": str(validator_exit),
                "STUB_LINES": str(validator_lines),
            },
            input=event,
            capture_output=True,
            text=True,
            check=False,
        )

    def validator_runs(self) -> list[str]:
        return self.runs.read_text().splitlines() if self.runs.exists() else []

    def test_failed_validation_blocks_with_the_end_of_the_log(self) -> None:
        self.leave_uncommitted_work()

        result = self.stop(
            "claude",
            event='{"stop_hook_active": false}',
            validator_exit=1,
            validator_lines=60,
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("validator line 60\n", result.stderr)
        self.assertIn("validator line 21\n", result.stderr)
        self.assertNotIn("validator line 20\n", result.stderr)

        full_log = re.search(r"^Full log: (.+)$", result.stderr, re.MULTILINE)
        assert full_log is not None, result.stderr
        self.assertIn("validator line 1\n", Path(full_log.group(1)).read_text())

    def test_devin_reads_its_block_decision_from_stdout(self) -> None:
        self.leave_uncommitted_work()

        result = self.stop("devin", event="{}", validator_exit=1)

        self.assertEqual(result.returncode, 2)
        decision = json.loads(result.stdout)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("validator line 3", decision["reason"])

    def test_passing_validation_finishes_silently(self) -> None:
        self.leave_uncommitted_work()

        result = self.stop("codex", event="{}")

        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))
        # Work in progress is rarely staged, so the gate must tell the
        # validator to accept untracked skill files.
        self.assertEqual(self.validator_runs(), ["1"])
        self.assertEqual(list(self.logs.iterdir()), [])

    def test_a_gate_that_already_blocked_does_not_block_again(self) -> None:
        self.leave_uncommitted_work()

        for harness in ("claude", "codex", "devin"):
            with self.subTest(harness=harness):
                result = self.stop(
                    harness, event='{"stop_hook_active": true}', validator_exit=1
                )
                self.assertEqual(result.returncode, 0)

        self.assertEqual(self.validator_runs(), [])

    def test_an_unreadable_event_still_validates(self) -> None:
        self.leave_uncommitted_work()

        for event in ("", "not json"):
            with self.subTest(event=event):
                result = self.stop("claude", event=event, validator_exit=1)
                self.assertEqual(result.returncode, 2)

    def test_clean_tree_matching_its_upstream_skips_validation(self) -> None:
        self.push_to_upstream()

        result = self.stop("amp", validator_exit=1)

        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.validator_runs(), [])

    def test_unpushed_commits_are_validated(self) -> None:
        self.push_to_upstream()
        self.leave_uncommitted_work()
        self.commit_everything("local only")

        result = self.stop("opencode", validator_exit=1)

        self.assertEqual(result.returncode, 2)

    def test_a_branch_without_an_upstream_is_validated(self) -> None:
        result = self.stop("amp", validator_exit=1)

        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
