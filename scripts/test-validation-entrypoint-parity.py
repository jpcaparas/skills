#!/usr/bin/env python3
"""Regression tests for active validation entrypoint detection."""

from __future__ import annotations

import json
import os
import shlex
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
CANONICAL_VALIDATOR_SOURCE: Final = SCRIPT_DIR / "validate-all-skills.sh"
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
      - name: Set Up Python
        if: ${{{{ !env.ACT || runner.os == 'Linux' }}}}
        uses: actions/setup-python@v6
        with:
          python-version: "3.11"
      - name: Set Up Node
        if: ${{{{ !env.ACT || runner.os == 'Linux' }}}}
        uses: actions/setup-node@v6
        with:
          node-version: "24"
      - name: Set Up Bun
        if: ${{{{ !env.ACT || runner.os == 'Linux' }}}}
        uses: oven-sh/setup-bun@v2
        with:
          bun-version: "1.3.11"
      - name: Prepare Local macOS Toolchain (act)
        if: ${{{{ env.ACT && runner.os == 'macOS' }}}}
        shell: bash
        run: |
          validation_python="${{SKILLS_ACT_MACOS_PYTHON:-}}"
          validation_node="${{SKILLS_ACT_MACOS_NODE:-}}"
          validation_npm="${{SKILLS_ACT_MACOS_NPM:-}}"
          validation_npx="${{SKILLS_ACT_MACOS_NPX:-}}"
          validation_bun="${{SKILLS_ACT_MACOS_BUN:-}}"
          "$validation_python" -c 'import sys, venv; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'
          "$validation_node" --version
          "$validation_bun" --version
          "$validation_python" -m venv "$RUNNER_TEMP/validation-venv"
          ln -s "$validation_node" "$RUNNER_TEMP/bin/node"
          ln -s "$validation_npm" "$RUNNER_TEMP/bin/npm"
          ln -s "$validation_npx" "$RUNNER_TEMP/bin/npx"
          ln -s "$validation_bun" "$RUNNER_TEMP/bin/bun"
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

    def test_rejects_drift_from_hosted_python_311(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            'python-version: "3.11"',
            'python-version: "3.12"',
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "must pin python-version to '3.11'")

    def test_rejects_drift_from_hosted_node_24(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            'node-version: "24"',
            'node-version: "26"',
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "must pin node-version to '24'")

    def test_rejects_drift_from_hosted_bun_1311(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            'bun-version: "1.3.11"',
            'bun-version: "1.4.0"',
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "must pin bun-version to '1.3.11'")

    def test_rejects_bare_python_for_local_macos_bootstrap(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            '"$validation_python" -m venv "$RUNNER_TEMP/validation-venv"',
            'python3 -m venv "$RUNNER_TEMP/validation-venv"',
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, "must not bootstrap from bare python3")

    def test_rejects_commented_local_macos_runtime_selection(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            '          validation_bun="${SKILLS_ACT_MACOS_BUN:-}"',
            '          # validation_bun="${SKILLS_ACT_MACOS_BUN:-}"',
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(
            result,
            "must contain 'validation_bun=\"${SKILLS_ACT_MACOS_BUN:-}\"'",
        )

    def test_rejects_quoted_output_decoys_for_local_macos_toolchain(self) -> None:
        requirements = (
            (
                'validation_python="${SKILLS_ACT_MACOS_PYTHON:-}"',
                'validation_python="${SKILLS_ACT_MACOS_PYTHON:-}"',
            ),
            (
                'validation_node="${SKILLS_ACT_MACOS_NODE:-}"',
                'validation_node="${SKILLS_ACT_MACOS_NODE:-}"',
            ),
            (
                'validation_npm="${SKILLS_ACT_MACOS_NPM:-}"',
                'validation_npm="${SKILLS_ACT_MACOS_NPM:-}"',
            ),
            (
                'validation_npx="${SKILLS_ACT_MACOS_NPX:-}"',
                'validation_npx="${SKILLS_ACT_MACOS_NPX:-}"',
            ),
            (
                'validation_bun="${SKILLS_ACT_MACOS_BUN:-}"',
                'validation_bun="${SKILLS_ACT_MACOS_BUN:-}"',
            ),
            (
                '"$validation_python" -c \'import sys, venv; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)\'',
                "sys.version_info >= (3, 11)",
            ),
            ('"$validation_node" --version', '"$validation_node" --version'),
            ('"$validation_bun" --version', '"$validation_bun" --version'),
            (
                '"$validation_python" -m venv "$RUNNER_TEMP/validation-venv"',
                '"$validation_python" -m venv',
            ),
            (
                'ln -s "$validation_node" "$RUNNER_TEMP/bin/node"',
                'ln -s "$validation_node"',
            ),
            (
                'ln -s "$validation_npm" "$RUNNER_TEMP/bin/npm"',
                'ln -s "$validation_npm"',
            ),
            (
                'ln -s "$validation_npx" "$RUNNER_TEMP/bin/npx"',
                'ln -s "$validation_npx"',
            ),
            (
                'ln -s "$validation_bun" "$RUNNER_TEMP/bin/bun"',
                'ln -s "$validation_bun"',
            ),
        )

        for active_line, expected_fragment in requirements:
            with self.subTest(active_line=active_line):
                workflow = VALID_WORKFLOW.replace(
                    f"          {active_line}",
                    f"          echo {shlex.quote(active_line)}",
                    1,
                )

                result = self.run_validator(workflow=workflow)

                self.assert_rejected(
                    result,
                    f"must contain {expected_fragment!r}",
                )

    def test_rejects_dead_local_macos_runtime_selection(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            '          validation_node="${SKILLS_ACT_MACOS_NODE:-}"',
            "          if false; then\n"
            '            validation_node="${SKILLS_ACT_MACOS_NODE:-}"\n'
            "          fi",
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(
            result,
            "must contain 'validation_node=\"${SKILLS_ACT_MACOS_NODE:-}\"'",
        )

    def test_rejects_commented_local_macos_npm_shim(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            '          ln -s "$validation_npm" "$RUNNER_TEMP/bin/npm"',
            '          # ln -s "$validation_npm" "$RUNNER_TEMP/bin/npm"',
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, 'must contain \'ln -s "$validation_npm"\'')

    def test_rejects_dead_local_macos_npx_shim(self) -> None:
        workflow = VALID_WORKFLOW.replace(
            '          ln -s "$validation_npx" "$RUNNER_TEMP/bin/npx"',
            "          if false; then\n"
            '            ln -s "$validation_npx" "$RUNNER_TEMP/bin/npx"\n'
            "          fi",
        )

        result = self.run_validator(workflow=workflow)

        self.assert_rejected(result, 'must contain \'ln -s "$validation_npx"\'')

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


class ValidationToolchainSelectionTests(unittest.TestCase):
    """Exercise the canonical validator's local interpreter preflight."""

    def create_fixture(self, root: Path) -> Path:
        scripts_dir = root / "scripts"
        scripts_dir.mkdir(parents=True)
        shutil.copy2(CANONICAL_VALIDATOR_SOURCE, scripts_dir / "validate-all-skills.sh")
        (scripts_dir / "test-validate-ci-with-act.sh").write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "python3 --child-probe\n"
            "bun --child-probe\n"
            "npx --child-probe\n"
            "exit 73\n",
            encoding="utf-8",
        )
        return root / "python-invocations.log"

    def create_fake_bun(self, executable: Path) -> None:
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_text(
            "#!/usr/bin/env sh\n"
            f"printf '%s|%s\\n' {shlex.quote(str(executable))} \"$*\" "
            ">>\"${FAKE_BUN_LOG:?}\"\n"
            "exit 0\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)

    def create_fake_npx(self, executable: Path) -> None:
        executable.parent.mkdir(parents=True, exist_ok=True)
        node = executable.parent / "node"
        node.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
        node.chmod(0o755)
        executable.write_text(
            "#!/usr/bin/env sh\n"
            "command -v node >/dev/null 2>&1 || exit 86\n"
            f"printf '%s|%s\\n' {shlex.quote(str(executable))} \"$*\" "
            ">>\"${FAKE_NPX_LOG:?}\"\n"
            "exit 0\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)

    def create_fake_python(
        self,
        executable: Path,
        *,
        include_bun: bool = True,
        include_npx: bool = True,
    ) -> None:
        executable.parent.mkdir(parents=True, exist_ok=True)
        executable.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            f"printf '%s|%s\\n' {shlex.quote(str(executable))} \"$*\" "
            ">>\"${FAKE_PYTHON_LOG:?}\"\n"
            "if [ \"${1:-}\" = \"-c\" ]; then\n"
            "    case \"${2:-}\" in\n"
            "        *version_info*) exit \"${FAKE_PYTHON_VERSION_STATUS:-0}\" ;;\n"
            "        *openpyxl*) exit \"${FAKE_PYTHON_DEPENDENCY_STATUS:-0}\" ;;\n"
            "        *sys.executable*)\n"
            "            executable_dir=\"$(cd \"$(dirname \"$0\")\" && pwd -P)\"\n"
            "            printf '%s/%s\\n' \"$executable_dir\" \"$(basename \"$0\")\"\n"
            "            exit 0\n"
            "            ;;\n"
            "    esac\n"
            "fi\n"
            "exit 0\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)
        if include_bun:
            self.create_fake_bun(executable.parent / "bun")
        if include_npx:
            self.create_fake_npx(executable.parent / "npx")

    def run_fixture(
        self,
        root: Path,
        log: Path,
        *,
        path_python: Path,
        override: Path | None = None,
        npx_override: Path | None = None,
        version_status: int = 0,
        dependency_status: int = 0,
    ) -> subprocess.CompletedProcess[str]:
        environment = {
            **os.environ,
            "PATH": f"{path_python.parent}:/usr/bin:/bin",
            "HOME": str(root / "home"),
            "FAKE_PYTHON_LOG": str(log),
            "FAKE_BUN_LOG": str(log),
            "FAKE_NPX_LOG": str(log),
            "FAKE_PYTHON_VERSION_STATUS": str(version_status),
            "FAKE_PYTHON_DEPENDENCY_STATUS": str(dependency_status),
        }
        environment.pop("BUN_INSTALL", None)
        environment.pop("SKILLS_VALIDATION_BUN", None)
        environment.pop("SKILLS_VALIDATION_NODE", None)
        if npx_override is None:
            environment.pop("SKILLS_VALIDATION_NPX", None)
        else:
            environment["SKILLS_VALIDATION_NPX"] = str(npx_override)
        if override is None:
            environment.pop("SKILLS_VALIDATION_PYTHON", None)
        else:
            environment["SKILLS_VALIDATION_PYTHON"] = str(override)
        return subprocess.run(
            ["bash", "scripts/validate-all-skills.sh"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )

    def test_explicit_python_override_wins_over_repository_venv(self) -> None:
        with tempfile.TemporaryDirectory(prefix="validation-toolchain-test.") as temp_dir:
            root = Path(temp_dir)
            log = self.create_fixture(root)
            venv_python = root / ".venv" / "bin" / "python3"
            override_python = root / "override" / "bin" / "python3"
            self.create_fake_python(venv_python)
            self.create_fake_python(override_python)

            result = self.run_fixture(
                root,
                log,
                path_python=venv_python,
                override=override_python,
            )

            self.assertEqual(result.returncode, 73, result.stderr)
            invocations = log.read_text(encoding="utf-8")
            self.assertIn(str(override_python), invocations)
            self.assertNotIn(str(venv_python), invocations)

    def test_repository_venv_wins_over_path_python(self) -> None:
        with tempfile.TemporaryDirectory(prefix="validation-toolchain-test.") as temp_dir:
            root = Path(temp_dir)
            log = self.create_fixture(root)
            venv_python = root / ".venv" / "bin" / "python3"
            path_python = root / "path" / "bin" / "python3"
            self.create_fake_python(venv_python)
            self.create_fake_python(path_python)

            result = self.run_fixture(root, log, path_python=path_python)

            self.assertEqual(result.returncode, 73, result.stderr)
            invocations = log.read_text(encoding="utf-8")
            self.assertIn(str(venv_python), invocations)
            self.assertNotIn(str(path_python), invocations)

    def test_python_older_than_311_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="validation-toolchain-test.") as temp_dir:
            root = Path(temp_dir)
            log = self.create_fixture(root)
            python = root / "path" / "bin" / "python3"
            self.create_fake_python(python)

            result = self.run_fixture(root, log, path_python=python, version_status=1)

            self.assertEqual(result.returncode, 1)
            self.assertIn("requires Python 3.11 or newer", result.stderr)

    def test_missing_python_packages_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="validation-toolchain-test.") as temp_dir:
            root = Path(temp_dir)
            log = self.create_fixture(root)
            python = root / "path" / "bin" / "python3"
            self.create_fake_python(python)

            result = self.run_fixture(root, log, path_python=python, dependency_status=1)

            self.assertEqual(result.returncode, 1)
            self.assertIn("requires the pinned Python packages", result.stderr)

    def test_child_python3_uses_the_selected_environment(self) -> None:
        with tempfile.TemporaryDirectory(prefix="validation-toolchain-test.") as temp_dir:
            root = Path(temp_dir)
            log = self.create_fixture(root)
            python = root / "selected" / "bin" / "python3"
            self.create_fake_python(python)

            result = self.run_fixture(root, log, path_python=python, override=python)

            self.assertEqual(result.returncode, 73, result.stderr)
            self.assertIn(
                f"{python}|--child-probe",
                log.read_text(encoding="utf-8"),
            )

    def test_versioned_only_python_override_is_exposed_to_children(self) -> None:
        with tempfile.TemporaryDirectory(prefix="validation-toolchain-test.") as temp_dir:
            root = Path(temp_dir)
            log = self.create_fixture(root)
            path_python = root / "path" / "bin" / "python3"
            versioned_python = root / "selected" / "bin" / "python3.13"
            self.create_fake_python(path_python)
            self.create_fake_python(versioned_python)

            result = self.run_fixture(
                root,
                log,
                path_python=path_python,
                override=versioned_python,
            )

            self.assertEqual(result.returncode, 73, result.stderr)
            self.assertIn(
                f"{versioned_python}|--child-probe",
                log.read_text(encoding="utf-8"),
            )

    def test_missing_bun_fails_before_skill_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="validation-toolchain-test.") as temp_dir:
            root = Path(temp_dir)
            log = self.create_fixture(root)
            python = root / "path" / "bin" / "python3"
            self.create_fake_python(python, include_bun=False)

            result = self.run_fixture(root, log, path_python=python)

            self.assertEqual(result.returncode, 1)
            self.assertIn("requires Bun for the scaffold-hooks probes", result.stderr)

    def test_standard_bun_install_is_added_to_child_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="validation-toolchain-test.") as temp_dir:
            root = Path(temp_dir)
            log = self.create_fixture(root)
            python = root / "path" / "bin" / "python3"
            standard_bun = root / "home" / ".bun" / "bin" / "bun"
            self.create_fake_python(python, include_bun=False)
            self.create_fake_bun(standard_bun)

            result = self.run_fixture(root, log, path_python=python)

            self.assertEqual(result.returncode, 73, result.stderr)
            self.assertIn(
                f"{standard_bun}|--child-probe",
                log.read_text(encoding="utf-8"),
            )

    def test_missing_npx_fails_before_skill_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="validation-toolchain-test.") as temp_dir:
            root = Path(temp_dir)
            log = self.create_fixture(root)
            python = root / "path" / "bin" / "python3"
            self.create_fake_python(python, include_npx=False)

            result = self.run_fixture(root, log, path_python=python)

            self.assertEqual(result.returncode, 1)
            self.assertIn("requires npx for the skills discovery probe", result.stderr)

    def test_explicit_npx_override_uses_its_sibling_node(self) -> None:
        with tempfile.TemporaryDirectory(prefix="validation-toolchain-test.") as temp_dir:
            root = Path(temp_dir)
            log = self.create_fixture(root)
            python = root / "path" / "bin" / "python3"
            npx = root / "node-toolchain" / "bin" / "npx"
            self.create_fake_python(python, include_npx=False)
            self.create_fake_npx(npx)
            shadow_python = npx.parent / "python3"
            shadow_python.write_text(
                "#!/usr/bin/env sh\n"
                "printf 'shadow-python|%s\\n' \"$*\" >>\"${FAKE_PYTHON_LOG:?}\"\n"
                "exit 0\n",
                encoding="utf-8",
            )
            shadow_python.chmod(0o755)

            result = self.run_fixture(
                root,
                log,
                path_python=python,
                npx_override=npx,
            )

            self.assertEqual(result.returncode, 73, result.stderr)
            invocations = log.read_text(encoding="utf-8")
            self.assertIn(f"{npx}|--child-probe", invocations)
            self.assertIn(f"{python}|--child-probe", invocations)
            self.assertNotIn("shadow-python|--child-probe", invocations)


if __name__ == "__main__":
    unittest.main()
