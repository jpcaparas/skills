#!/usr/bin/env python3
"""Regression tests for environment-sensitive command probes."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import probe_implicit_token_savings


class DockerProbeTests(unittest.TestCase):
    """Distinguish an unavailable daemon from malformed command output."""

    def run_fake_docker(self, script_body: str) -> dict[str, object]:
        # Keep the controlled executable off hardened system temp mounts that
        # use noexec, while retaining automatic cleanup on macOS and Ubuntu.
        with tempfile.TemporaryDirectory(
            prefix=".docker-probe-regression.",
            dir=SCRIPT_DIR.parent,
        ) as temp_dir:
            fake_bin = Path(temp_dir)
            docker_path = fake_bin / "docker"
            docker_path.write_text(
                "#!/bin/sh\nset -eu\n" + script_body,
                encoding="utf-8",
            )
            docker_path.chmod(0o755)
            fake_path = f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"
            with patch.dict(os.environ, {"PATH": fake_path}):
                return probe_implicit_token_savings.probe_docker()

    def test_skips_an_installed_cli_without_a_daemon(self) -> None:
        result = self.run_fake_docker(
            'if [ "${1:-}" = "info" ]; then exit 1; fi\nexit 97\n'
        )

        self.assertTrue(result["passed"])
        self.assertTrue(result["skipped"])
        self.assertIn("daemon is unavailable", result["detail"])

    def test_accepts_json_rows_from_an_available_daemon(self) -> None:
        result = self.run_fake_docker(
            'if [ "${1:-}" = "info" ]; then exit 0; fi\n'
            "printf '%s\\n' '{\"Names\":\"web\"}'\n"
        )

        self.assertTrue(result["passed"])
        self.assertFalse(result["skipped"])

    def test_rejects_malformed_rows_from_an_available_daemon(self) -> None:
        result = self.run_fake_docker(
            'if [ "${1:-}" = "info" ]; then exit 0; fi\n'
            "printf '%s\\n' 'not-json'\n"
        )

        self.assertFalse(result["passed"])
        self.assertFalse(result["skipped"])


if __name__ == "__main__":
    unittest.main()
