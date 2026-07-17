#!/usr/bin/env python3
"""Integration checks for scaffold-hooks."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


EXPECTED_HARNESSES = {"claude", "codex", "copilot", "devin", "opencode"}
SHELL_PLAN_HARNESSES = ("claude", "codex", "copilot", "devin")


def run(
    cmd: list[str],
    cwd: Path | None = None,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        check=False,
        capture_output=True,
        text=True,
        env=merged_env,
    )


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def invalid_plan_item_cases() -> list[tuple[str, str, object]]:
    """Return behaviorally distinct malformed scripts/commands partitions."""
    return [
        ("scripts-null", "scripts", None),
        ("scripts-string", "scripts", "scripts/check.sh"),
        ("scripts-object", "scripts", {"path": "scripts/check.sh"}),
        ("scripts-wrong-item", "scripts", [False]),
        (
            "scripts-args-object",
            "scripts",
            [{"path": "scripts/check.sh", "args": {}, "cwd": "."}],
        ),
        (
            "scripts-args-wrong-item",
            "scripts",
            [{"path": "scripts/check.sh", "args": ["ok", 7], "cwd": "."}],
        ),
        (
            "scripts-cwd-object",
            "scripts",
            [{"path": "scripts/check.sh", "args": [], "cwd": {}}],
        ),
        ("commands-null", "commands", None),
        ("commands-string", "commands", "true"),
        ("commands-object", "commands", {"command": "true"}),
        ("commands-wrong-item", "commands", [False]),
        (
            "commands-cwd-object",
            "commands",
            [{"command": "true", "cwd": {}}],
        ),
    ]


def harness_plan_validation_errors(skill_path: Path, temp_root: Path) -> list[str]:
    """Exercise every shell scaffolder against the malformed plan matrix."""
    errors: list[str] = []
    diagnostic = "Plan file has invalid scripts or commands configuration."

    for harness in SHELL_PLAN_HARNESSES:
        harness_root = skill_path / "harnesses" / harness
        base_plan = load_json(harness_root / "templates" / "hook-plan.example.json")
        project = temp_root / f"invalid-plan-{harness}-project"
        project.mkdir()

        for case_name, field, invalid_value in invalid_plan_item_cases():
            plan = copy.deepcopy(base_plan)
            enabled_events = plan.get("enabled_events")
            if not isinstance(enabled_events, list) or not enabled_events:
                errors.append(f"{harness} template has no enabled event for plan validation")
                break
            first_event = enabled_events[0]
            if not isinstance(first_event, dict):
                errors.append(f"{harness} template has a non-object enabled event")
                break
            first_event[field] = copy.deepcopy(invalid_value)

            plan_path = temp_root / f"invalid-plan-{harness}-{case_name}.json"
            plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
            command = [
                "bash",
                str(harness_root / "scripts" / "scaffold_hooks.sh"),
                "--project",
                str(project),
                "--plan",
                str(plan_path),
                "--dry-run",
            ]
            if harness == "codex":
                command.extend(["--ensure-feature", "off"])

            proc = run(command, cwd=harness_root)
            if proc.returncode == 0 or diagnostic not in proc.stderr:
                errors.append(
                    f"{harness} accepted or misreported {case_name}: "
                    f"status={proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
                )

        if any(project.iterdir()):
            errors.append(f"{harness} malformed-plan dry runs wrote into the target project")

    return errors


def manifest_row_stream_errors(skill_path: Path, temp_root: Path) -> list[str]:
    """Prove a late manifest-row producer failure cannot write a prefix."""
    errors: list[str] = []
    real_jq = shutil.which("jq")
    if not real_jq:
        return ["jq is required for manifest row stream regression checks"]

    fake_bin = temp_root / "late-row-fake-bin"
    fake_bin.mkdir()
    fake_jq = fake_bin / "jq"
    write(
        fake_jq,
        "#!/usr/bin/env bash\n"
        "set -u\n"
        "for argument in \"$@\"; do\n"
        "    case \"$argument\" in\n"
        "        *\".events[]\"*\"@tsv\"*)\n"
        "            printf 'LateFailure\\tlate_failure.sh\\tforced prefix row\\tguidance\\tguidance\\tguidance\\n'\n"
        "            exit 5\n"
        "            ;;\n"
        "    esac\n"
        "done\n"
        "exec \"$REAL_JQ\" \"$@\"\n",
    )
    fake_jq.chmod(0o755)

    for harness in SHELL_PLAN_HARNESSES:
        source_root = skill_path / "harnesses" / harness
        harness_root = temp_root / f"late-row-{harness}-harness"
        shutil.copytree(source_root, harness_root)
        project = temp_root / f"late-row-{harness}-project"
        project.mkdir()
        run(["git", "init", "-q"], cwd=project)

        command = [
            "bash",
            str(harness_root / "scripts" / "scaffold_hooks.sh"),
            "--project",
            str(project),
            "--plan",
            str(harness_root / "templates" / "hook-plan.example.json"),
        ]
        if harness == "codex":
            command.extend(["--ensure-feature", "off"])

        proc = run(
            command,
            cwd=harness_root,
            env={
                "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
                "REAL_JQ": real_jq,
            },
        )
        prefix_artifact = (
            project
            / ".github"
            / "copilot"
            / "hooks"
            / "generated"
            / "events"
            / "late_failure.sh"
            if harness == "copilot"
            else project / "hooks" / "late-failure" / "script.sh"
        )
        if (
            proc.returncode == 0
            or "Failed to read complete" not in proc.stderr
            or prefix_artifact.exists()
        ):
            errors.append(
                f"{harness} consumed a partial manifest row stream: "
                f"status={proc.returncode}, prefix={prefix_artifact.exists()}\n"
                f"stdout={proc.stdout}\nstderr={proc.stderr}"
            )

    return errors


RUNTIME_VALIDATION_SHELL = r"""
runtime_path="$1"
runner_name="$2"
payload="$3"
project_root="$4"
marker_path="$5"

source "$runtime_path"
export AGENT_HOOK_HARNESS="claude"
export CLAUDE_PROJECT_DIR="$project_root"
export GITHUB_WORKSPACE="$project_root"
export HOOK_INPUT='{}'
export RUNTIME_MARKER_PATH="$marker_path"

case "$runner_name" in
    config_scripts)
        ADAPTER_CONFIG_JSON="$payload"
        export ADAPTER_CONFIG_JSON
        run_configured_scripts "$(config_scripts_json)"
        ;;
    config_commands)
        ADAPTER_CONFIG_JSON="$payload"
        export ADAPTER_CONFIG_JSON
        run_configured_commands "$(config_commands_json)"
        ;;
    run_configured_scripts|run_configured_commands)
        "$runner_name" "$payload"
        ;;
    *)
        exit 99
        ;;
esac
"""


def runtime_plan_validation_errors(
    runtime_path: Path,
    project: Path,
    *,
    supports_config_accessors: bool,
) -> list[str]:
    """Prove malformed runtime plans fail before any configured effect runs."""
    errors: list[str] = []
    runtime_content = runtime_path.read_text(encoding="utf-8")
    if supports_config_accessors:
        for required_marker in [
            "hook_should_skip_event()",
            "validate_code_change_extensions_json()",
            "preflight_configured_effects()",
            "run_hook_event()",
            'command_statuses=("${PIPESTATUS[@]}")',
            "unable to inspect code changes; running configured checks.",
        ]:
            if required_marker not in runtime_content:
                errors.append(
                    f"{runtime_path.name} is missing shared event marker: {required_marker}"
                )
    marker = project / "runtime-plan-validation.marker"
    marker_script = project / "scripts" / "runtime-plan-validation.sh"
    write(
        marker_script,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'executed\\n' > \"$RUNTIME_MARKER_PATH\"\n",
    )
    marker_script.chmod(0o755)

    script_path = str(marker_script.relative_to(project))
    marker_command = "printf 'executed\\n' > \"$RUNTIME_MARKER_PATH\""
    cases = [
        ("scripts-null", "run_configured_scripts", "null", "invalid scripts configuration"),
        ("scripts-string", "run_configured_scripts", '"bad"', "invalid scripts configuration"),
        ("scripts-object", "run_configured_scripts", "{}", "invalid scripts configuration"),
        ("scripts-wrong-item", "run_configured_scripts", "[false]", "invalid scripts configuration"),
        ("scripts-malformed-json", "run_configured_scripts", "[", "invalid scripts configuration"),
        (
            "scripts-bad-args",
            "run_configured_scripts",
            json.dumps([{"path": script_path, "args": {}, "cwd": "."}]),
            "invalid scripts configuration",
        ),
        (
            "scripts-bad-arg-item",
            "run_configured_scripts",
            json.dumps([{"path": script_path, "args": [7], "cwd": "."}]),
            "invalid scripts configuration",
        ),
        (
            "scripts-bad-cwd",
            "run_configured_scripts",
            json.dumps([{"path": script_path, "args": [], "cwd": {}}]),
            "invalid scripts configuration",
        ),
        ("commands-null", "run_configured_commands", "null", "invalid commands configuration"),
        ("commands-string", "run_configured_commands", '"bad"', "invalid commands configuration"),
        ("commands-object", "run_configured_commands", "{}", "invalid commands configuration"),
        ("commands-wrong-item", "run_configured_commands", "[false]", "invalid commands configuration"),
        ("commands-malformed-json", "run_configured_commands", "[", "invalid commands configuration"),
        (
            "commands-bad-cwd",
            "run_configured_commands",
            json.dumps([{"command": marker_command, "cwd": {}}]),
            "invalid commands configuration",
        ),
    ]
    if supports_config_accessors:
        cases.extend(
            [
                (
                    "config-scripts-null",
                    "config_scripts",
                    '{"scripts":null}',
                    "invalid scripts configuration",
                ),
                (
                    "config-commands-null",
                    "config_commands",
                    '{"commands":null}',
                    "invalid commands configuration",
                ),
            ]
        )

    for case_name, runner_name, payload, diagnostic in cases:
        marker.unlink(missing_ok=True)
        proc = run(
            [
                "bash",
                "-c",
                RUNTIME_VALIDATION_SHELL,
                "runtime-validation",
                str(runtime_path),
                runner_name,
                payload,
                str(project),
                str(marker),
            ],
            cwd=project,
        )
        if proc.returncode == 0 or diagnostic not in proc.stderr or marker.exists():
            errors.append(
                f"{runtime_path.name} did not fail closed for {case_name}: "
                f"status={proc.returncode}, marker={marker.exists()}\n"
                f"stdout={proc.stdout}\nstderr={proc.stderr}"
            )

    for runner_name in ("run_configured_scripts", "run_configured_commands"):
        proc = run(
            [
                "bash",
                "-c",
                RUNTIME_VALIDATION_SHELL,
                "runtime-validation",
                str(runtime_path),
                runner_name,
                "[]",
                str(project),
                str(marker),
            ],
            cwd=project,
        )
        if proc.returncode != 0:
            errors.append(
                f"{runtime_path.name} rejected valid empty {runner_name}: {proc.stderr}"
            )

    return errors


def seed_legacy_project(project: Path) -> None:
    run(["git", "init", "-q"], cwd=project)
    write(
        project / ".claude" / "settings.json",
        json.dumps(
            {
                "hooks": {
                    "UserPromptSubmit": [
                        {"hooks": [{"type": "prompt", "prompt": "custom prompt hook", "timeout": 5}]}
                    ],
                    "Stop": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": '"$CLAUDE_PROJECT_DIR"/.claude/hooks/generated/events/stop.sh',
                                    "timeout": 30,
                                }
                            ]
                        }
                    ],
                }
            },
            indent=2,
        )
        + "\n",
    )
    write(
        project / ".codex" / "hooks.json",
        json.dumps(
            {
                "hooks": {
                    "Stop": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "/usr/bin/env bash -lc 'exec \"$(git rev-parse --show-toplevel)/.codex/hooks/generated/events/stop.sh\"'",
                                    "timeout": 30,
                                }
                            ]
                        }
                    ]
                }
            },
            indent=2,
        )
        + "\n",
    )
    write(
        project / ".devin" / "hooks.v1.json",
        json.dumps(
            {
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "/workspace/.devin/hooks/generated/events/stop.sh",
                                "timeout": 30,
                            }
                        ]
                    }
                ]
            },
            indent=2,
        )
        + "\n",
    )
    for legacy_root in [
        project / ".claude" / "hooks" / "generated",
        project / ".codex" / "hooks" / "generated",
        project / ".devin" / "hooks" / "generated",
    ]:
        write(legacy_root / "manifest.json", "{}\n")
        write(legacy_root / "events" / "stop.sh", "#!/usr/bin/env bash\nexit 0\n")
        os.chmod(legacy_root / "events" / "stop.sh", 0o755)
    write(project / ".claude" / "hooks" / "plan.json", '{"enabled_events":[{"name":"Stop","timeout":30}]}\n')
    write(project / ".codex" / "hooks" / "plan.json", '{"enabled_events":[{"name":"Stop","timeout":30}]}\n')
    write(
        project / ".opencode" / "plugins" / ".managed" / "manifest.json",
        json.dumps(
            {
                "deployment": "local-files",
                "mode": "overhaul",
                "module_format": "ts",
                "plugin_root": ".opencode/plugins",
                "managed_files": ["opencode_hook_project_session_lifecycle.ts"],
                "enabled_plugins": [
                    {
                        "name": "old-lifecycle",
                        "pattern": "lifecycle-action",
                        "filename": "opencode_hook_project_session_lifecycle.ts",
                        "context_script": "hooks/opencode-session-created/opencode.sh",
                        "action_script": "hooks/opencode-session-idle/opencode.sh",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
    )
    write(
        project / ".opencode" / "plugins" / "opencode_hook_project_session_lifecycle.ts",
        "export const Plugin = async () => ({})\n",
    )
    write(project / ".opencode" / "plugins" / "README.md", "# OpenCode Hooks\n\nGenerated by scaffold-hooks.\n")
    write(project / ".opencode" / "package.json", '{"dependencies":{"@opencode-ai/plugin":"1.15.10"}}\n')
    write(project / "hooks" / "opencode-session-created" / "script.sh", "#!/usr/bin/env bash\necho '[opencode-hook] missing delegate'\n")
    write(
        project / "hooks" / "opencode-session-created" / "opencode.sh",
        "#!/usr/bin/env bash\nexport OPENCODE_HOOK_EVENT=opencode-session-created\n",
    )
    write(project / "hooks" / "opencode-session-idle" / "script.sh", "#!/usr/bin/env bash\necho '[opencode-hook] missing delegate'\n")
    write(
        project / "hooks" / "opencode-session-idle" / "opencode.sh",
        "#!/usr/bin/env bash\nexport OPENCODE_HOOK_EVENT=opencode-session-idle\n",
    )
    write(project / "scripts" / "agent-session-context.sh", "#!/usr/bin/env bash\nexit 0\n")
    write(project / "scripts" / "validate-project.sh", "#!/usr/bin/env bash\nexit 0\n")
    write(project / "src" / "fixture.ts", "export const fixture = true;\n")
    os.chmod(project / "scripts" / "agent-session-context.sh", 0o755)
    os.chmod(project / "scripts" / "validate-project.sh", 0o755)


def text_contains_legacy(project: Path) -> bool:
    needles = [".claude/hooks/generated", ".codex/hooks/generated", ".devin/hooks/generated"]
    for rel_path in [".claude/settings.json", ".codex/hooks.json", ".devin/hooks.v1.json"]:
        path = project / rel_path
        if path.exists() and any(needle in path.read_text(encoding="utf-8") for needle in needles):
            return True
    return False


def test_skill(skill_path: Path) -> dict:
    results = {
        "skill": skill_path.name,
        "passed": True,
        "tests_found": 0,
        "files_verified": {"passed": 0, "total": 0},
        "integration_checks": {"passed": 0, "total": 0},
        "errors": [],
    }

    evals_path = skill_path / "evals" / "evals.json"
    if not evals_path.is_file():
        results["errors"].append("evals/evals.json is missing")
        results["passed"] = False
    else:
        evals = load_json(evals_path).get("evals", [])
        results["tests_found"] = len(evals)
        for item in evals:
            for rel_path in item.get("files", []):
                results["files_verified"]["total"] += 1
                if (skill_path / rel_path).exists():
                    results["files_verified"]["passed"] += 1
                else:
                    results["errors"].append(f"Eval references missing file: {rel_path}")
                    results["passed"] = False

    plan = load_json(skill_path / "templates" / "hook-plan.example.json")
    if set(plan.get("harnesses", [])) != EXPECTED_HARNESSES:
        results["errors"].append("Plan must enable all supported harnesses by default")
        results["passed"] = False
    for harness in EXPECTED_HARNESSES:
        if harness not in plan.get("plans", {}):
            results["errors"].append(f"Plan missing nested {harness} config")
            results["passed"] = False

    scaffold_script = skill_path / "scripts" / "scaffold_all_hooks.sh"
    if not os.access(scaffold_script, os.X_OK):
        results["errors"].append("scripts/scaffold_all_hooks.sh must be executable")
        results["passed"] = False

    with tempfile.TemporaryDirectory(prefix="scaffold-hooks-test-") as tmp:
        temp_root = Path(tmp)
        results["integration_checks"]["total"] += 1
        invalid_plan_errors = harness_plan_validation_errors(skill_path, temp_root)
        if invalid_plan_errors:
            results["errors"].extend(invalid_plan_errors)
            results["passed"] = False
        else:
            results["integration_checks"]["passed"] += 1

        results["integration_checks"]["total"] += 1
        row_stream_errors = manifest_row_stream_errors(skill_path, temp_root)
        if row_stream_errors:
            results["errors"].extend(row_stream_errors)
            results["passed"] = False
        else:
            results["integration_checks"]["passed"] += 1

        project = Path(tmp) / "project"
        project.mkdir()
        seed_legacy_project(project)
        all_harnesses = "claude,codex,copilot,devin,opencode"

        detected_project = Path(tmp) / "detected-project"
        detected_project.mkdir()
        write(
            detected_project / ".claude" / "settings.json",
            json.dumps(
                {
                    "hooks": {
                        "Stop": [
                            {
                                "hooks": [
                                    {
                                        "type": "command",
                                        "command": "npm run agent:stop",
                                    }
                                ]
                            }
                        ]
                    }
                },
                indent=2,
            )
            + "\n",
        )
        detected_dry_run = run([str(scaffold_script), "--project", str(detected_project), "--dry-run"])
        results["integration_checks"]["total"] += 1
        if (
            detected_dry_run.returncode == 0
            and "harnesses:       claude" in detected_dry_run.stdout
            and "selection source: detected-hooks" in detected_dry_run.stdout
        ):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append(
                "bare hook refresh did not use the detected harness set: "
                f"{detected_dry_run.stdout}\n{detected_dry_run.stderr}"
            )
            results["passed"] = False

        custom_plan = Path(tmp) / "custom-plan-without-harnesses.json"
        custom_plan_data = load_json(skill_path / "templates" / "hook-plan.example.json")
        custom_plan_data.pop("harnesses", None)
        custom_plan.write_text(json.dumps(custom_plan_data, indent=2) + "\n", encoding="utf-8")
        detected_custom_plan_dry_run = run(
            [str(scaffold_script), "--project", str(detected_project), "--plan", str(custom_plan), "--dry-run"]
        )
        results["integration_checks"]["total"] += 1
        if (
            detected_custom_plan_dry_run.returncode == 0
            and "harnesses:       claude" in detected_custom_plan_dry_run.stdout
            and "selection source: detected-hooks" in detected_custom_plan_dry_run.stdout
        ):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append(
                "custom plan without harnesses expanded beyond detected hooks: "
                f"{detected_custom_plan_dry_run.stdout}\n{detected_custom_plan_dry_run.stderr}"
            )
            results["passed"] = False

        dry_run = run(
            [str(scaffold_script), "--project", str(project), "--harnesses", all_harnesses, "--dry-run"]
        )
        results["integration_checks"]["total"] += 1
        if dry_run.returncode == 0 and "scaffold_all_hooks.sh dry run complete" in dry_run.stdout:
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append(f"dry-run failed: {dry_run.stdout}\n{dry_run.stderr}")
            results["passed"] = False

        completed = run([str(scaffold_script), "--project", str(project), "--harnesses", all_harnesses])
        results["integration_checks"]["total"] += 1
        if completed.returncode == 0:
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append(f"scaffold_all_hooks.sh failed: {completed.stdout}\n{completed.stderr}")
            results["passed"] = False

        expected_paths = [
            "hooks/README.md",
            "hooks/.state/scaffold-hooks/manifest.json",
            "hooks/stop/script.sh",
            "hooks/stop/claude.sh",
            "hooks/stop/claude.json",
            "hooks/stop/codex.sh",
            "hooks/stop/codex.json",
            "hooks/stop/devin.sh",
            "hooks/stop/devin.json",
            ".claude/settings.json",
            ".codex/hooks.json",
            ".devin/hooks.v1.json",
            "opencode.json",
            ".opencode/hook/hooks.md",
            ".opencode/hook/README.md",
            ".opencode/hook/.managed/manifest.json",
        ]
        results["integration_checks"]["total"] += 1
        missing = [rel_path for rel_path in expected_paths if not (project / rel_path).exists()]
        if not missing:
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("Scaffold missing expected paths: " + ", ".join(missing))
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        universal_manifest = load_json(project / "hooks" / ".state" / "scaffold-hooks" / "manifest.json")
        provenance = universal_manifest.get("scaffold_hooks", {})
        if (
            provenance.get("schema_version") == 1
            and provenance.get("skill_name") == "scaffold-hooks"
            and provenance.get("skill_version")
            and provenance.get("generator", {}).get("sha256")
            and provenance.get("plan_sha256")
            and universal_manifest.get("harness_selection_source") == "cli"
        ):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("Universal manifest did not record scaffold provenance and plan/generator hashes")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        if not text_contains_legacy(project):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("Final configs still contain legacy generated hook roots")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        if not any((project / rel).exists() for rel in [
            ".claude/hooks/generated",
            ".codex/hooks/generated",
            ".devin/hooks/generated",
        ]):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("Legacy managed generated folders were not cleaned up")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        opencode_config = load_json(project / "opencode.json")
        opencode_hooks = (project / ".opencode" / "hook" / "hooks.md").read_text(encoding="utf-8")
        legacy_opencode_paths = [
            project / ".opencode" / "plugins" / ".managed",
            project / ".opencode" / "plugins" / "opencode_hook_project_session_lifecycle.ts",
            project / ".opencode" / "package.json",
            project / "hooks" / "opencode-session-created" / "opencode.sh",
            project / "hooks" / "opencode-session-idle" / "opencode.sh",
        ]
        if (
            "opencode-froggy" in opencode_config.get("plugin", [])
            and "# BEGIN scaffold-hooks managed opencode-froggy" in opencode_hooks
            and not any(path.exists() for path in legacy_opencode_paths)
        ):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("OpenCode Froggy migration did not enable Froggy or remove legacy managed artifacts")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        claude_settings = load_json(project / ".claude" / "settings.json")
        user_prompt = claude_settings.get("hooks", {}).get("UserPromptSubmit", [])
        if any("custom prompt hook" in json.dumps(group) for group in user_prompt):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("Custom Claude prompt hook was not preserved")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        claude_commands = [
            hook.get("command", "")
            for groups in claude_settings.get("hooks", {}).values()
            for group in groups
            for hook in group.get("hooks", [])
            if hook.get("type") == "command"
        ]
        if (
            "${CLAUDE_PROJECT_DIR}/hooks/stop/claude.sh" in claude_commands
            and not any('"$CLAUDE_PROJECT_DIR"' in command for command in claude_commands)
        ):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("Claude settings reintroduced embedded quotes around CLAUDE_PROJECT_DIR")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        runtime_content = (project / "hooks" / "lib" / "agent-hook-runtime.sh").read_text(encoding="utf-8")
        stop_config = load_json(project / "hooks" / "stop" / "codex.json")
        quiet_code_change_probe = any(
            token in runtime_content for token in ["grep -Eiq", "grep -Eq", "grep -q", ">/dev/null"]
        )
        fail_safe_code_change_probe = (
            'command_statuses=("${PIPESTATUS[@]}")' in runtime_content
            and "unable to inspect code changes; running configured checks." in runtime_content
        )
        if (
            "hook_has_code_changes()" in runtime_content
            and quiet_code_change_probe
            and fail_safe_code_change_probe
            and "head -1" not in runtime_content
            and stop_config.get("run_on_code_changes") is True
            and "ts" in stop_config.get("code_change_extensions", [])
        ):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("Universal scaffold did not preserve the quiet shared code-change Stop gate")
            results["passed"] = False

        runtime_targets = [
            (
                "universal shared runtime",
                project / "hooks" / "lib" / "agent-hook-runtime.sh",
                True,
            ),
            (
                "Copilot generated runtime",
                project
                / ".github"
                / "copilot"
                / "hooks"
                / "generated"
                / "lib"
                / "common.sh",
                False,
            ),
        ]
        repository_root = skill_path.parent.parent
        checked_in_runtime = repository_root / "hooks" / "lib" / "agent-hook-runtime.sh"
        if (repository_root / ".git").exists() and checked_in_runtime.exists():
            runtime_targets.append(("checked-in shared runtime", checked_in_runtime, True))

        if (repository_root / ".git").exists():
            results["integration_checks"]["total"] += 1
            checked_in_event_scripts = sorted((repository_root / "hooks").glob("*/script.sh"))
            stale_event_scripts = [
                script_path
                for script_path in checked_in_event_scripts
                if 'run_hook_event handle_event "$@"' not in script_path.read_text(
                    encoding="utf-8"
                )
            ]
            if checked_in_event_scripts and not stale_event_scripts:
                results["integration_checks"]["passed"] += 1
            else:
                stale_names = ", ".join(
                    str(script_path.relative_to(repository_root))
                    for script_path in stale_event_scripts
                )
                results["errors"].append(
                    "Checked-in event scripts bypass the shared event guard"
                    + (f": {stale_names}" if stale_names else "")
                )
                results["passed"] = False

        for runtime_label, runtime_path, supports_config_accessors in runtime_targets:
            results["integration_checks"]["total"] += 1
            if not runtime_path.exists():
                results["errors"].append(f"{runtime_label} is missing: {runtime_path}")
                results["passed"] = False
                continue
            runtime_errors = runtime_plan_validation_errors(
                runtime_path,
                project,
                supports_config_accessors=supports_config_accessors,
            )
            if runtime_errors:
                results["errors"].extend(runtime_errors)
                results["passed"] = False
            else:
                results["integration_checks"]["passed"] += 1

        write(project / "scripts" / "empty-args-ok.sh", "#!/usr/bin/env bash\nexit 0\n")
        os.chmod(project / "scripts" / "empty-args-ok.sh", 0o755)
        codex_stop_config_path = project / "hooks" / "stop" / "codex.json"
        codex_stop_config = load_json(codex_stop_config_path)
        codex_stop_config["scripts"] = [
            {
                "label": "empty args regression",
                "path": "scripts/empty-args-ok.sh",
                "args": [],
                "cwd": ".",
            }
        ]
        codex_stop_config_path.write_text(json.dumps(codex_stop_config, indent=2) + "\n", encoding="utf-8")

        results["integration_checks"]["total"] += 1
        empty_args = run(
            ["bash", str(project / "hooks" / "stop" / "codex.sh")],
            cwd=project,
            input_text='{"session_id":"empty-args-regression"}',
        )
        if empty_args.returncode == 0 and empty_args.stdout == "":
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append(
                "Generated Codex Stop hook failed empty args regression: "
                f"status={empty_args.returncode}\nstdout={empty_args.stdout}\nstderr={empty_args.stderr}"
            )
            results["passed"] = False

        pollution_filename = "src/stdout-pollution-regression.ts"
        write(project / pollution_filename, "export const stdoutPollutionRegression = true;\n")
        git_add = run(["git", "add", pollution_filename], cwd=project)
        if git_add.returncode != 0:
            results["errors"].append(f"git add failed for stdout pollution regression: {git_add.stderr}")
            results["passed"] = False

        write(
            project / "scripts" / "fail-stop-check.sh",
            "#!/usr/bin/env bash\nprintf 'stop check failed\\n' >&2\nexit 1\n",
        )
        os.chmod(project / "scripts" / "fail-stop-check.sh", 0o755)
        codex_stop_config = load_json(codex_stop_config_path)
        codex_stop_config["scripts"] = [
            {
                "label": "stdout pollution regression",
                "path": "scripts/fail-stop-check.sh",
                "args": [],
                "cwd": ".",
            }
        ]
        codex_stop_config_path.write_text(json.dumps(codex_stop_config, indent=2) + "\n", encoding="utf-8")

        results["integration_checks"]["total"] += 1
        polluted_stop = run(
            ["bash", str(project / "hooks" / "stop" / "codex.sh")],
            cwd=project,
            input_text='{"session_id":"stdout-pollution-regression"}',
        )
        polluted_stop_json = None
        polluted_stop_json_error = ""
        try:
            polluted_stop_json = json.loads(polluted_stop.stdout)
        except json.JSONDecodeError as exc:
            polluted_stop_json_error = f"json error={exc}\n"

        if (
            polluted_stop.returncode == 0
            and polluted_stop_json is not None
            and polluted_stop_json.get("decision") == "block"
            and pollution_filename not in polluted_stop.stdout
        ):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append(
                "Generated Codex Stop hook leaked helper output or failed to block cleanly: "
                f"status={polluted_stop.returncode}\n{polluted_stop_json_error}"
                f"stdout={polluted_stop.stdout}\nstderr={polluted_stop.stderr}"
            )
            results["passed"] = False

    for harness in sorted(EXPECTED_HARNESSES):
        harness_dir = skill_path / "harnesses" / harness
        results["integration_checks"]["total"] += 1
        suite = run(
            [sys.executable, str(harness_dir / "scripts" / "test_skill.py"), str(harness_dir)],
        )
        if suite.returncode == 0:
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append(
                f"Harness suite failed: harnesses/{harness}\n{suite.stdout}\n{suite.stderr}"
            )
            results["passed"] = False

    return results


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: test_skill.py /path/to/skill", file=sys.stderr)
        return 2
    results = test_skill(Path(sys.argv[1]).resolve())
    print(f"Skill: {results['skill']}")
    print(f"Tests found: {results['tests_found']}")
    print(f"Files verified: {results['files_verified']['passed']}/{results['files_verified']['total']}")
    print(
        "Integration checks: "
        f"{results['integration_checks']['passed']}/{results['integration_checks']['total']}"
    )
    if not results["passed"]:
        print("\nFAIL:")
        for error in results["errors"]:
            print(f"- {error}")
        return 1
    print("\nPASS: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
