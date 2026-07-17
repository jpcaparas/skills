#!/usr/bin/env python3
"""Regression tests for active validation entrypoint detection."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Final


SCRIPT_DIR: Final = Path(__file__).resolve().parent
VALIDATOR_SOURCE: Final = SCRIPT_DIR / "check-validation-entrypoint-parity.py"
YAML_VALIDATION_SOURCE: Final = SCRIPT_DIR / "yaml_validation.py"
STOP_CHECK_SOURCE: Final = SCRIPT_DIR / "agent-stop-checks.sh"
SNAPSHOT_SOURCE: Final = SCRIPT_DIR / "agent-repo-snapshot.sh"
CANONICAL_COMMAND: Final = "bash scripts/validate-all-skills.sh"
ACT_MATRIX_COMMAND: Final = "bash scripts/validate-ci-with-act.sh --matrix"
ACT_UBUNTU_COMMAND: Final = "bash scripts/validate-ci-with-act.sh --ubuntu"
ACT_MACOS_COMMAND: Final = "bash scripts/validate-ci-with-act.sh --macos"
CANONICAL_PRE_PUSH: Final = (
    'exec "$(dirname -- "$0")/../scripts/run-pnpm.sh" run validate'
)

VALID_WORKFLOW: Final = f"""\
name: Validate Skills
jobs:
  validate:
    runs-on: ${{{{ matrix.os }}}}
    strategy:
      fail-fast: false
      matrix:
        os:
          - ubuntu-24.04
          - macos-15
    steps:
      - name: Validate Skills
        run: {CANONICAL_COMMAND}
"""

VALID_PACKAGE_JSON: Final = json.dumps(
    {
        "scripts": {
            "validate": CANONICAL_COMMAND,
            "validate:act": ACT_MATRIX_COMMAND,
            "validate:act:ubuntu": ACT_UBUNTU_COMMAND,
            "validate:act:macos": ACT_MACOS_COMMAND,
        }
    }
)

VALID_STOP_CHECKS: Final = """\
#!/usr/bin/env bash
if [ -n "${AGENT_HOOK_HARNESS:-}" ]; then
    bash "$REPO_ROOT/scripts/validate-all-skills.sh" >&2
else
    bash "$REPO_ROOT/scripts/validate-all-skills.sh"
fi
"""


class ValidationEntrypointParityTests(unittest.TestCase):
    """Exercise validators against isolated repository-shaped fixtures."""

    def run_validator(
        self,
        *,
        workflow: str = VALID_WORKFLOW,
        pre_push: str = f"#!/usr/bin/env sh\n{CANONICAL_PRE_PUSH}\n",
        stop_checks: str = VALID_STOP_CHECKS,
        package_json: str = VALID_PACKAGE_JSON,
    ) -> subprocess.CompletedProcess[str]:
        """Run the parity validator against a temporary repository fixture."""
        with tempfile.TemporaryDirectory(prefix="entrypoint-parity-test.") as temp_dir:
            repo_root = Path(temp_dir)
            self.write_fixture(
                repo_root,
                workflow,
                pre_push,
                stop_checks,
                package_json,
            )
            return subprocess.run(
                [sys.executable, "scripts/check-validation-entrypoint-parity.py"],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )

    def write_fixture(
        self,
        repo_root: Path,
        workflow: str,
        pre_push: str,
        stop_checks: str,
        package_json: str = VALID_PACKAGE_JSON,
    ) -> None:
        """Create the smallest repository shape consumed by the validator."""
        (repo_root / "scripts").mkdir(parents=True)
        (repo_root / ".github/workflows").mkdir(parents=True)
        (repo_root / ".husky").mkdir(parents=True)
        (repo_root / "hooks/stop").mkdir(parents=True)

        shutil.copy2(
            VALIDATOR_SOURCE,
            repo_root / "scripts/check-validation-entrypoint-parity.py",
        )
        shutil.copy2(
            YAML_VALIDATION_SOURCE,
            repo_root / "scripts/yaml_validation.py",
        )
        (repo_root / "package.json").write_text(package_json, encoding="utf-8")
        (repo_root / ".github/workflows/validate-skills.yml").write_text(
            workflow,
            encoding="utf-8",
        )
        (repo_root / ".husky/pre-push").write_text(pre_push, encoding="utf-8")
        (repo_root / "scripts/agent-stop-checks.sh").write_text(
            stop_checks,
            encoding="utf-8",
        )

        stop_config = json.dumps(
            {"scripts": [{"path": "scripts/agent-stop-checks.sh"}]}
        )
        for harness in ("claude", "codex", "devin"):
            (repo_root / f"hooks/stop/{harness}.json").write_text(
                stop_config,
                encoding="utf-8",
            )

    def assert_rejected(
        self,
        result: subprocess.CompletedProcess[str],
        expected_error: str,
    ) -> None:
        """Require a fixture to fail for the intended parity reason."""
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(expected_error, result.stderr)

    def test_accepts_active_canonical_entrypoints(self) -> None:
        result = self.run_validator()

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_missing_act_matrix_package_entrypoint(self) -> None:
        package_json = json.dumps(
            {
                "scripts": {
                    "validate": CANONICAL_COMMAND,
                    "validate:act:ubuntu": ACT_UBUNTU_COMMAND,
                    "validate:act:macos": ACT_MACOS_COMMAND,
                }
            }
        )

        result = self.run_validator(package_json=package_json)

        self.assert_rejected(result, "scripts.validate:act must equal")

    def test_rejects_wrong_act_ubuntu_package_entrypoint(self) -> None:
        package_json = json.dumps(
            {
                "scripts": {
                    "validate": CANONICAL_COMMAND,
                    "validate:act": ACT_MATRIX_COMMAND,
                    "validate:act:ubuntu": ACT_MACOS_COMMAND,
                    "validate:act:macos": ACT_MACOS_COMMAND,
                }
            }
        )

        result = self.run_validator(package_json=package_json)

        self.assert_rejected(result, "scripts.validate:act:ubuntu must equal")

    def test_rejects_wrong_act_macos_package_entrypoint(self) -> None:
        package_json = json.dumps(
            {
                "scripts": {
                    "validate": CANONICAL_COMMAND,
                    "validate:act": ACT_MATRIX_COMMAND,
                    "validate:act:ubuntu": ACT_UBUNTU_COMMAND,
                    "validate:act:macos": ACT_UBUNTU_COMMAND,
                }
            }
        )

        result = self.run_validator(package_json=package_json)

        self.assert_rejected(result, "scripts.validate:act:macos must equal")

    def test_rejects_workflow_with_a_hard_coded_runner(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            "runs-on: ${{ matrix.os }}",
            "runs-on: ubuntu-24.04",
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "must use runs-on")

    def test_rejects_workflow_without_the_macos_matrix_leg(self) -> None:
        workflow = VALID_WORKFLOW.replace("          - macos-15\n", "")

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "matrix.os must contain exactly")

    def test_rejects_duplicate_workflow_matrix_leg(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            "          - macos-15\n",
            "          - macos-15\n          - macos-15\n",
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "matrix.os must contain exactly")

    def test_rejects_fail_fast_workflow_matrix(self) -> None:
        workflow = VALID_WORKFLOW.replace("fail-fast: false", "fail-fast: true")

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "matrix must set fail-fast to false")

    def test_rejects_workflow_matrix_exclusion(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            "    steps:\n",
            "        exclude:\n          - os: macos-15\n    steps:\n",
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "matrix must contain only the 'os' axis")

    def test_rejects_workflow_matrix_inclusion(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            "    steps:\n",
            "        include:\n          - os: ubuntu-24.04\n    steps:\n",
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "matrix must contain only the 'os' axis")

    def test_rejects_workflow_matrix_with_an_extra_axis(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            "          - macos-15\n",
            "          - macos-15\n        python: ['3.11', '3.12']\n",
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "matrix must contain only the 'os' axis")

    def test_rejects_workflow_command_that_exists_only_in_a_comment(self) -> None:
        workflow = f"""\
name: Validate Skills
jobs:
  validate:
    steps:
      # run: {CANONICAL_COMMAND}
      - name: Validate Skills
        run: echo validation-bypassed
"""

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "'Validate Skills' step must run")

    def test_rejects_canonical_command_in_a_decoy_workflow_step(self) -> None:
        workflow = f"""\
name: Validate Skills
jobs:
  validate:
    steps:
      - name: Decoy
        run: {CANONICAL_COMMAND}
      - name: Validate Skills
        run: echo validation-bypassed
"""

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "'Validate Skills' step must run")

    def test_rejects_disabled_workflow_validation_step(self) -> None:
        workflow = f"""\
name: Validate Skills
jobs:
  validate:
    steps:
      - name: Validate Skills
        if: false
        run: {CANONICAL_COMMAND}
"""

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "must not be conditional")

    def test_rejects_disabled_workflow_validation_job(self) -> None:
        workflow = f"""\
name: Validate Skills
jobs:
  validate:
    if: false
    steps:
      - name: Validate Skills
        run: {CANONICAL_COMMAND}
"""

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "'validate' job must not be conditional")

    def test_rejects_nonblocking_workflow_validation_job(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            "    runs-on:",
            "    continue-on-error: true\n    runs-on:",
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "'validate' job must block")

    def test_rejects_nonblocking_workflow_validation_step(self) -> None:
        workflow = f"""\
name: Validate Skills
jobs:
  validate:
    steps:
      - name: Validate Skills
        continue-on-error: true
        run: {CANONICAL_COMMAND}
"""

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "must block on validation failure")

    def test_rejects_pre_push_command_that_exists_only_in_a_comment(self) -> None:
        pre_push = f"#!/usr/bin/env sh\n# {CANONICAL_PRE_PUSH}\nexit 0\n"

        result = self.run_validator(pre_push=pre_push)

        self.assert_rejected(result, ".husky/pre-push must execute only")

    def test_rejects_stop_command_that_exists_only_in_a_comment(self) -> None:
        stop_checks = """\
#!/usr/bin/env bash
# bash "$REPO_ROOT/scripts/validate-all-skills.sh"
exit 0
"""

        result = self.run_validator(stop_checks=stop_checks)

        self.assert_rejected(result, "must actively invoke")

    def test_rejects_stop_command_hidden_in_a_false_branch(self) -> None:
        stop_checks = """\
#!/usr/bin/env bash
if false; then
    bash "$REPO_ROOT/scripts/validate-all-skills.sh" >&2
    bash "$REPO_ROOT/scripts/validate-all-skills.sh"
fi
"""

        result = self.run_validator(stop_checks=stop_checks)

        self.assert_rejected(result, "must actively invoke")

    def test_rejects_stop_command_hidden_in_a_heredoc(self) -> None:
        stop_checks = """\
#!/usr/bin/env bash
cat <<'NOT_A_COMMAND'
bash "$REPO_ROOT/scripts/validate-all-skills.sh" >&2
bash "$REPO_ROOT/scripts/validate-all-skills.sh"
NOT_A_COMMAND
"""

        result = self.run_validator(stop_checks=stop_checks)

        self.assert_rejected(result, "must actively invoke")

    def test_rejects_stop_command_hidden_in_an_unused_function(self) -> None:
        stop_checks = """\
#!/usr/bin/env bash
not_called() {
    bash "$REPO_ROOT/scripts/validate-all-skills.sh" >&2
    bash "$REPO_ROOT/scripts/validate-all-skills.sh"
}
exit 0
"""

        result = self.run_validator(stop_checks=stop_checks)

        self.assert_rejected(result, "must actively invoke")

    def test_rejects_duplicate_workflow_keys(self) -> None:
        workflow = f"""\
name: Validate Skills
jobs:
  validate:
    steps:
      - name: Validate Skills
        run: echo bypassed
    steps:
      - name: Validate Skills
        run: {CANONICAL_COMMAND}
"""

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "contains invalid YAML")

    def test_rejects_duplicate_package_json_keys(self) -> None:
        with tempfile.TemporaryDirectory(prefix="entrypoint-parity-test.") as temp_dir:
            repo_root = Path(temp_dir)
            self.write_fixture(
                repo_root,
                VALID_WORKFLOW,
                f"#!/usr/bin/env sh\n{CANONICAL_PRE_PUSH}\n",
                VALID_STOP_CHECKS,
            )
            (repo_root / "package.json").write_text(
                '{"scripts":{"validate":"echo bypassed",'
                f'"validate":"{CANONICAL_COMMAND}"}}',
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, "scripts/check-validation-entrypoint-parity.py"],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assert_rejected(result, "duplicate JSON member: validate")

    def test_rejects_nonstandard_package_json_constants(self) -> None:
        with tempfile.TemporaryDirectory(prefix="entrypoint-parity-test.") as temp_dir:
            repo_root = Path(temp_dir)
            self.write_fixture(
                repo_root,
                VALID_WORKFLOW,
                f"#!/usr/bin/env sh\n{CANONICAL_PRE_PUSH}\n",
                VALID_STOP_CHECKS,
            )
            (repo_root / "package.json").write_text(
                '{"scripts":{"validate":"bash scripts/validate-all-skills.sh"},'
                '"invalid":NaN}',
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, "scripts/check-validation-entrypoint-parity.py"],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assert_rejected(result, "non-standard JSON constant: NaN")

    def test_stop_checks_execute_the_canonical_validator_for_both_modes(self) -> None:
        """Run the real stop pipeline in both output modes against a fake marker."""
        with tempfile.TemporaryDirectory(prefix="entrypoint-stop-probe.") as temp_dir:
            workspace = Path(temp_dir)
            repo_root = workspace / "repo"
            scripts_dir = repo_root / "scripts"
            scripts_dir.mkdir(parents=True)
            shutil.copy2(STOP_CHECK_SOURCE, scripts_dir / "agent-stop-checks.sh")
            shutil.copy2(SNAPSHOT_SOURCE, scripts_dir / "agent-repo-snapshot.sh")

            # Keep probe evidence outside the repository so the stop hook's
            # concurrent-mutation guard sees a stable project snapshot.
            marker = workspace / "canonical-validator-invocations.txt"
            (scripts_dir / "validate-all-skills.sh").write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "printf '%s\\n' \"${AGENT_HOOK_HARNESS:-interactive}\" "
                ">>\"${VALIDATOR_MARKER:?VALIDATOR_MARKER must be set}\"\n",
                encoding="utf-8",
            )
            for path in scripts_dir.iterdir():
                path.chmod(path.stat().st_mode | 0o111)

            subprocess.run(
                ["git", "init", "--quiet"],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
            base_environment = {
                **os.environ,
                "SKILLS_AGENT_STOP_FORCE": "1",
                "VALIDATOR_MARKER": str(marker),
            }
            for harness in (None, "probe"):
                environment = dict(base_environment)
                if harness is None:
                    environment.pop("AGENT_HOOK_HARNESS", None)
                else:
                    environment["AGENT_HOOK_HARNESS"] = harness
                result = subprocess.run(
                    ["bash", "scripts/agent-stop-checks.sh"],
                    cwd=repo_root,
                    check=False,
                    capture_output=True,
                    text=True,
                    env=environment,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

            self.assertEqual(
                marker.read_text(encoding="utf-8").splitlines(),
                ["interactive", "probe"],
            )


if __name__ == "__main__":
    unittest.main()
