#!/usr/bin/env python3
"""Behavioural tests for the scaffolders and the hooks they generate.

Everything runs offline in disposable projects: only events with scripts or
commands are emitted, malformed plans are rejected before any write, stubs and
legacy generated roots are migrated away without losing custom hooks, and the
generated Stop/permission hooks translate failures into each harness's protocol.
"""

from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCAFFOLD_ALL = SKILL / "scripts" / "scaffold_all_hooks.sh"
EXAMPLE_PLAN = SKILL / "templates" / "hook-plan.example.json"
SHELL_PLAN_HARNESSES = ("claude", "codex", "copilot", "devin")
ALL_HARNESSES = "claude,codex,copilot,devin,opencode"
STOP_PAYLOAD = json.dumps({"hook_event_name": "Stop", "stop_hook_active": False})


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



def tmp_root(test: unittest.TestCase) -> Path:
    """Scratch space that can hold executables, even where /tmp is noexec."""
    directory = tempfile.TemporaryDirectory(dir=os.environ.get("SKILLS_EXECUTABLE_TMPDIR"))
    test.addCleanup(directory.cleanup)
    return Path(directory.name)


def scaffold_harness(harness: str, project: Path, plan: Path) -> None:
    command = [
        "bash",
        str(SKILL / "harnesses" / harness / "scripts" / "scaffold_hooks.sh"),
        "--project",
        str(project),
        "--plan",
        str(plan),
    ]
    if harness == "codex":
        command.extend(["--ensure-feature", "off"])
    result = run(command)
    if result.returncode != 0:
        raise AssertionError(f"{harness} scaffold failed:\n{result.stdout}\n{result.stderr}")


def plan_with(harness: str, tmp: Path, edit) -> Path:
    plan = load_json(SKILL / "harnesses" / harness / "templates" / "hook-plan.example.json")
    edit(plan)
    path = tmp / f"{harness}-plan.json"
    path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return path


def event(plan: dict, name: str) -> dict:
    return next(item for item in plan["enabled_events"] if item["name"] == name)


class PlanValidationTests(unittest.TestCase):
    def test_malformed_scripts_and_commands_are_rejected_without_writing(self) -> None:
        self.assertEqual([], harness_plan_validation_errors(SKILL, tmp_root(self)))

    def test_late_manifest_row_failure_does_not_leave_a_partial_scaffold(self) -> None:
        self.assertEqual([], manifest_row_stream_errors(SKILL, tmp_root(self)))


def universal_plan(tmp: Path, edit=lambda plan: None, name: str = "universal-plan.json") -> Path:
    plan = load_json(EXAMPLE_PLAN)
    edit(plan)
    path = tmp / name
    path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return path


def scaffold_all(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    result = run([str(SCAFFOLD_ALL), "--project", str(project), *args])
    if result.returncode != 0:
        raise AssertionError(f"universal scaffold failed:\n{result.stdout}\n{result.stderr}")
    return result


def event_dirs(project: Path) -> set[str]:
    return {path.parent.name for path in (project / "hooks").glob("*/script.sh")}


def files_under(project: Path) -> set[str]:
    return {
        str(path.relative_to(project))
        for path in project.rglob("*")
        if path.is_file() and ".git" not in path.relative_to(project).parts
    }


class EmissionTests(unittest.TestCase):
    """Only events the plan gives scripts or commands get files and config."""

    def new_project(self) -> tuple[Path, Path]:
        tmp = tmp_root(self)
        project = tmp / "project"
        project.mkdir()
        run(["git", "init", "-q"], cwd=project)
        return tmp, project

    def test_only_events_with_behaviour_are_emitted(self) -> None:
        def add_empty_events(plan: dict) -> None:
            plan["plans"]["claude"]["enabled_events"].append(
                {"name": "PreToolUse", "matcher": "Bash", "timeout": 30, "scripts": [], "commands": []}
            )
            plan["plans"]["codex"]["enabled_events"].append({"name": "PermissionRequest", "scripts": [], "commands": []})
            plan["plans"]["devin"]["enabled_events"].append({"name": "PreToolUse", "matcher": "^exec$"})
            plan["plans"]["copilot"]["enabled_events"].append({"name": "preToolUse", "scripts": [], "commands": []})

        tmp, project = self.new_project()
        scaffold_all(project, "--plan", str(universal_plan(tmp, add_empty_events)), "--harnesses", ALL_HARNESSES)

        self.assertEqual({"session-start", "stop"}, event_dirs(project))
        self.assertEqual({"SessionStart", "Stop"}, set(load_json(project / ".claude" / "settings.json")["hooks"]))
        self.assertEqual({"SessionStart", "Stop"}, set(load_json(project / ".codex" / "hooks.json")["hooks"]))
        self.assertEqual({"SessionStart", "Stop"}, set(load_json(project / ".devin" / "hooks.v1.json")))
        self.assertEqual({"agentStop"}, set(load_json(project / ".github" / "hooks" / "copilot-hooks.json")["hooks"]))
        generated = project / ".github" / "copilot" / "hooks" / "generated" / "events"
        self.assertEqual({"agent-stop.sh"}, {path.name for path in generated.iterdir()})

    def test_no_plan_on_a_fresh_project_writes_nothing(self) -> None:
        _, project = self.new_project()
        before = files_under(project)
        result = run([str(SCAFFOLD_ALL), "--project", str(project), "--harnesses", ALL_HARNESSES])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(before, files_under(project))

    def test_plan_without_any_behaviour_writes_nothing(self) -> None:
        tmp, project = self.new_project()

        def strip_behaviour(plan: dict) -> None:
            for harness in SHELL_PLAN_HARNESSES:
                for item in plan["plans"][harness]["enabled_events"]:
                    item["scripts"] = []
                    item["commands"] = []
            plan["plans"]["opencode"]["hooks"] = [{"event": "session.idle", "actions": []}]

        scaffold_all(project, "--plan", str(universal_plan(tmp, strip_behaviour)), "--harnesses", ALL_HARNESSES)
        self.assertEqual(set(), event_dirs(project))
        self.assertFalse((project / "hooks").exists())
        self.assertFalse((project / ".github" / "copilot").exists())
        self.assertFalse((project / ".opencode").exists())

    def test_rerun_without_a_plan_keeps_the_recorded_behaviour(self) -> None:
        tmp, project = self.new_project()
        scaffold_all(project, "--plan", str(universal_plan(tmp)), "--harnesses", "claude,codex")
        scaffold_all(project)
        self.assertEqual({"session-start", "stop"}, event_dirs(project))
        self.assertEqual({"SessionStart", "Stop"}, set(load_json(project / ".claude" / "settings.json")["hooks"]))

    def test_event_dropped_from_the_plan_is_removed_with_its_config_entry(self) -> None:
        tmp, project = self.new_project()
        scaffold_all(project, "--plan", str(universal_plan(tmp)), "--harnesses", ALL_HARNESSES)

        def drop_session_start(plan: dict) -> None:
            for harness in ("claude", "codex", "devin"):
                plan["plans"][harness]["enabled_events"] = [
                    item for item in plan["plans"][harness]["enabled_events"] if item["name"] != "SessionStart"
                ]

        scaffold_all(
            project, "--plan", str(universal_plan(tmp, drop_session_start, "smaller.json")), "--harnesses", ALL_HARNESSES
        )
        self.assertEqual({"stop"}, event_dirs(project))
        self.assertFalse((project / "hooks" / "session-start").exists())
        self.assertEqual({"Stop"}, set(load_json(project / ".claude" / "settings.json")["hooks"]))
        self.assertEqual({"Stop"}, set(load_json(project / ".codex" / "hooks.json")["hooks"]))

    def test_refresh_removes_old_stubs_and_keeps_custom_work(self) -> None:
        tmp, project = self.new_project()
        stub_code = (SKILL / "harnesses" / "claude" / "templates" / "event-script.sh.tmpl").read_text(encoding="utf-8")
        old_stub = "# Canonical event script for PreToolUse.\n" + stub_code.replace("{{EVENT_NAME}}", "PreToolUse")
        for harness in ("claude", "codex", "devin"):
            write(
                project / "hooks" / "pre-tool-use" / f"{harness}.sh",
                f'#!/usr/bin/env bash\nexport AGENT_HOOK_HARNESS="{harness}"\nexport AGENT_HOOK_EVENT="PreToolUse"\n',
            )
            write(project / "hooks" / "pre-tool-use" / f"{harness}.json", '{"scripts": [], "commands": []}\n')
        write(project / "hooks" / "pre-tool-use" / "script.sh", old_stub)
        edited = old_stub.replace("    return 0\n", "    echo custom-notification-logic >&2\n    return 0\n")
        write(project / "hooks" / "notification" / "script.sh", edited)
        write(project / "hooks" / "notification" / "claude.sh", '#!/usr/bin/env bash\nexport AGENT_HOOK_HARNESS="claude"\n')
        write(project / "hooks" / "my-own-tool" / "run.sh", "#!/usr/bin/env bash\n")
        write(
            project / ".claude" / "settings.json",
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {"matcher": "Bash", "hooks": [{"type": "command", "command": "${CLAUDE_PROJECT_DIR}/hooks/pre-tool-use/claude.sh"}]},
                            {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo my-custom-guard"}]},
                        ]
                    }
                }
            ),
        )
        events = project / ".github" / "copilot" / "hooks" / "generated" / "events"
        write(
            events / "pre-tool-use.sh",
            "#!/usr/bin/env bash\n# Generated by scaffold-hooks for the GitHub Copilot preToolUse hook.\nPROJECT_SCRIPTS_JSON='[]'\n",
        )
        write(events / "handwritten.sh", "#!/usr/bin/env bash\n")

        scaffold_all(project, "--plan", str(universal_plan(tmp)), "--harnesses", "claude,codex,copilot,devin")

        self.assertFalse((project / "hooks" / "pre-tool-use").exists())
        self.assertFalse((events / "pre-tool-use.sh").exists())
        self.assertTrue((events / "handwritten.sh").exists())
        self.assertTrue((project / "hooks" / "my-own-tool" / "run.sh").exists())
        self.assertIn("custom-notification-logic", (project / "hooks" / "notification" / "script.sh").read_text(encoding="utf-8"))
        self.assertFalse((project / "hooks" / "notification" / "claude.sh").exists())
        settings = json.dumps(load_json(project / ".claude" / "settings.json"))
        self.assertIn("echo my-custom-guard", settings)
        self.assertNotIn("pre-tool-use/claude.sh", settings)
        self.assertEqual(
            {"session-start", "stop"},
            {path.parent.name for path in (project / "hooks").glob("*/claude.sh") if path.parent.name != "lib"},
        )


class HarnessSelectionTests(unittest.TestCase):
    def test_bare_run_refreshes_only_the_detected_harness(self) -> None:
        tmp = tmp_root(self)
        project = tmp / "project"
        write(
            project / ".claude" / "settings.json",
            json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "npm run agent:stop"}]}]}}),
        )
        plan = load_json(SKILL / "templates" / "hook-plan.example.json")
        plan.pop("harnesses")
        plan_path = tmp / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")

        for extra in ([], ["--plan", str(plan_path)]):
            with self.subTest(extra=extra):
                result = run([str(SCAFFOLD_ALL), "--project", str(project), "--dry-run", *extra])
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertIn("harnesses:       claude", result.stdout)
                self.assertIn("selection source: detected-hooks", result.stdout)


class UniversalMigrationTests(unittest.TestCase):
    """One scaffold over a project seeded with legacy generated roots for every harness."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._directory = tempfile.TemporaryDirectory(dir=os.environ.get("SKILLS_EXECUTABLE_TMPDIR"))
        cls.project = Path(cls._directory.name) / "project"
        cls.project.mkdir()
        seed_legacy_project(cls.project)
        result = run(
            [str(SCAFFOLD_ALL), "--project", str(cls.project), "--plan", str(EXAMPLE_PLAN), "--harnesses", ALL_HARNESSES]
        )
        if result.returncode != 0:
            raise AssertionError(f"universal scaffold failed:\n{result.stdout}\n{result.stderr}")

    @classmethod
    def tearDownClass(cls) -> None:
        cls._directory.cleanup()

    def test_dry_run_reports_completion_and_writes_nothing(self) -> None:
        fresh = tmp_root(self) / "fresh"
        fresh.mkdir()
        result = run([str(SCAFFOLD_ALL), "--project", str(fresh), "--harnesses", ALL_HARNESSES, "--dry-run"])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("scaffold_all_hooks.sh dry run complete", result.stdout)
        self.assertEqual([], list(fresh.iterdir()))

    def test_every_harness_gets_its_adapters_and_config(self) -> None:
        for relative in [
            "hooks/stop/script.sh",
            "hooks/stop/claude.sh",
            "hooks/stop/codex.sh",
            "hooks/stop/devin.sh",
            ".claude/settings.json",
            ".codex/hooks.json",
            ".devin/hooks.v1.json",
            ".github/hooks/copilot-hooks.json",
            "opencode.json",
            ".opencode/hook/hooks.md",
        ]:
            self.assertTrue((self.project / relative).exists(), relative)

    def test_manifest_records_provenance_and_selection_source(self) -> None:
        manifest = load_json(self.project / "hooks" / ".state" / "scaffold-hooks" / "manifest.json")
        provenance = manifest["scaffold_hooks"]
        self.assertEqual("scaffold-hooks", provenance["skill_name"])
        self.assertTrue(provenance["generator"]["sha256"])
        self.assertTrue(provenance["plan_sha256"])
        self.assertEqual("cli", manifest["harness_selection_source"])

    def test_legacy_generated_roots_are_removed_from_configs_and_disk(self) -> None:
        self.assertFalse(text_contains_legacy(self.project))
        for legacy in (".claude", ".codex", ".devin"):
            self.assertFalse((self.project / legacy / "hooks" / "generated").exists(), legacy)

    def test_opencode_legacy_plugin_is_replaced_by_froggy(self) -> None:
        config = load_json(self.project / "opencode.json")
        self.assertIn("opencode-froggy", config["plugin"])
        hooks = (self.project / ".opencode" / "hook" / "hooks.md").read_text(encoding="utf-8")
        self.assertIn("# BEGIN scaffold-hooks managed opencode-froggy", hooks)
        for legacy in [
            ".opencode/plugins/.managed",
            ".opencode/plugins/opencode_hook_project_session_lifecycle.ts",
            ".opencode/package.json",
            "hooks/opencode-session-created/opencode.sh",
            "hooks/opencode-session-idle/opencode.sh",
        ]:
            self.assertFalse((self.project / legacy).exists(), legacy)

    def test_custom_claude_hook_survives_and_command_path_is_unquoted(self) -> None:
        settings = load_json(self.project / ".claude" / "settings.json")
        self.assertIn("custom prompt hook", json.dumps(settings["hooks"]["UserPromptSubmit"]))
        commands = [
            hook["command"]
            for groups in settings["hooks"].values()
            for group in groups
            for hook in group["hooks"]
            if hook.get("type") == "command"
        ]
        self.assertIn("${CLAUDE_PROJECT_DIR}/hooks/stop/claude.sh", commands)
        self.assertFalse([command for command in commands if '"$CLAUDE_PROJECT_DIR"' in command])

    def test_rerun_keeps_custom_codex_hook_and_one_froggy_block(self) -> None:
        codex_path = self.project / ".codex" / "hooks.json"
        original = codex_path.read_text(encoding="utf-8")
        self.addCleanup(codex_path.write_text, original, encoding="utf-8")
        data = json.loads(original)
        data["hooks"].setdefault("SessionStart", []).append(
            {"matcher": "startup", "hooks": [{"type": "command", "command": "echo custom-session-start"}]}
        )
        codex_path.write_text(json.dumps(data), encoding="utf-8")

        result = run(
            [str(SCAFFOLD_ALL), "--project", str(self.project), "--plan", str(EXAMPLE_PLAN), "--harnesses", "codex,opencode"]
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("echo custom-session-start", codex_path.read_text(encoding="utf-8"))
        hooks = (self.project / ".opencode" / "hook" / "hooks.md").read_text(encoding="utf-8")
        self.assertEqual(1, hooks.count("BEGIN scaffold-hooks managed opencode-froggy"))

    def test_shared_runtimes_fail_closed_on_malformed_plans(self) -> None:
        for runtime, accessors in [
            (self.project / "hooks" / "lib" / "agent-hook-runtime.sh", True),
            (self.project / ".github" / "copilot" / "hooks" / "generated" / "lib" / "common.sh", False),
        ]:
            with self.subTest(runtime=runtime.name):
                self.assertEqual(
                    [],
                    runtime_plan_validation_errors(runtime, self.project, supports_config_accessors=accessors),
                )

    def test_codex_stop_accepts_empty_args(self) -> None:
        script = self.project / "scripts" / "empty-args-ok.sh"
        write(script, "#!/usr/bin/env bash\nexit 0\n")
        os.chmod(script, 0o755)
        result = self._run_codex_stop(script, "empty-args-regression")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)

    def test_codex_stop_blocks_cleanly_without_leaking_helper_output(self) -> None:
        filename = "src/stdout-pollution-regression.ts"
        write(self.project / filename, "export const stdoutPollutionRegression = true;\n")
        self.addCleanup((self.project / filename).unlink)
        subprocess.run(["git", "add", filename], cwd=self.project, check=True)
        self.addCleanup(subprocess.run, ["git", "reset", "-q", filename], cwd=self.project)
        script = self.project / "scripts" / "fail-stop-check.sh"
        write(script, "#!/usr/bin/env bash\nprintf 'stop check failed\\n' >&2\nexit 1\n")
        os.chmod(script, 0o755)

        result = self._run_codex_stop(script, "stdout-pollution-regression")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("block", json.loads(result.stdout)["decision"])
        self.assertNotIn(filename, result.stdout)

    def _run_codex_stop(self, script: Path, session_id: str) -> subprocess.CompletedProcess[str]:
        config_path = self.project / "hooks" / "stop" / "codex.json"
        original = config_path.read_text(encoding="utf-8")
        self.addCleanup(config_path.write_text, original, encoding="utf-8")
        config = json.loads(original)
        config["scripts"] = [{"label": session_id, "path": str(script.relative_to(self.project)), "args": [], "cwd": "."}]
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        return run(
            ["bash", str(self.project / "hooks" / "stop" / "codex.sh")],
            cwd=self.project,
            input_text=json.dumps({"session_id": session_id}),
        )


class ClaudeStopHookTests(unittest.TestCase):
    """The shared runtime behind the Claude, Codex and Devin Stop adapters."""

    def setUp(self) -> None:
        self.tmp = tmp_root(self)
        self.project = self.tmp / "project"
        self.project.mkdir()
        run(["git", "init", "-q"], cwd=self.project)
        write(self.project / "src" / "example.ts", "export const example = true;\n")
        self.marker = self.project / "configured-effect.marker"
        write(
            self.project / "scripts" / "agent-stop-checks.sh",
            "#!/usr/bin/env bash\nset -euo pipefail\n"
            "printf 'portable shared script %s\\n' \"${1:-}\" >&2\n"
            "[ -z \"${SCAFFOLD_HOOK_EFFECT_MARKER:-}\" ] || printf 'script\\n' >> \"$SCAFFOLD_HOOK_EFFECT_MARKER\"\n",
        )

        def edit(plan: dict) -> None:
            stop = event(plan, "Stop")
            stop["scripts"] = [{"label": "shared", "path": "scripts/agent-stop-checks.sh", "args": ["claude"], "cwd": "."}]
            stop["commands"] = [
                {
                    "label": "portable command",
                    "command": "printf 'portable hook command\\n' >&2; "
                    "[ -z \"${SCAFFOLD_HOOK_EFFECT_MARKER:-}\" ] || printf 'command\\n' >> \"$SCAFFOLD_HOOK_EFFECT_MARKER\"",
                    "cwd": ".",
                }
            ]
            plan["enabled_events"].append(
                {**stop, "name": "SubagentStop", "run_on_code_changes": False}
            )

        scaffold_harness("claude", self.project, plan_with("claude", self.tmp, edit))
        self.root = self.project / "hooks"
        self.stop = self.root / "stop" / "claude.sh"
        self.stop_config = self.root / "stop" / "claude.json"

    def run_stop(self, *, active: bool = False, event_script: Path | None = None, env: dict[str, str] | None = None):
        self.marker.unlink(missing_ok=True)
        payload = json.dumps({"hook_event_name": "Stop", "cwd": str(self.project), "stop_hook_active": active})
        return run(
            ["bash", str(event_script or self.stop)],
            cwd=self.project,
            input_text=payload,
            env={"SCAFFOLD_HOOK_EFFECT_MARKER": str(self.marker), **(env or {})},
        )

    def effects(self) -> set[str]:
        return set(self.marker.read_text(encoding="utf-8").split()) if self.marker.exists() else set()

    def commit_everything(self) -> None:
        run(["git", "add", "."], cwd=self.project)
        run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "--no-gpg-sign", "-qm", "fixture"],
            cwd=self.project,
        )

    def edit_stop_config(self, **changes: object) -> None:
        original = self.stop_config.read_text(encoding="utf-8")
        self.addCleanup(self.stop_config.write_text, original, encoding="utf-8")
        self.stop_config.write_text(json.dumps({**json.loads(original), **changes}), encoding="utf-8")

    def test_code_changes_run_the_configured_script_and_command(self) -> None:
        result = self.run_stop()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("portable shared script claude", result.stderr)
        self.assertIn("portable hook command", result.stderr)

    def test_active_stop_hook_skips_all_effects(self) -> None:
        result = self.run_stop(active=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(set(), self.effects())

    def test_subagent_stop_entry_honours_the_active_stop_guard(self) -> None:
        result = self.run_stop(active=True, event_script=self.root / "subagent-stop" / "claude.sh")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(set(), self.effects())

    def test_malformed_commands_are_rejected_before_any_script_runs(self) -> None:
        self.edit_stop_config(run_on_code_changes=False, commands=None)
        result = self.run_stop()
        self.assertIn("invalid commands configuration", result.stderr)
        self.assertEqual(set(), self.effects())

    def test_clean_tree_skips_checks(self) -> None:
        self.commit_everything()
        result = self.run_stop()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(set(), self.effects())

    def test_git_failure_runs_the_checks_instead_of_skipping_them(self) -> None:
        self.commit_everything()
        fake_bin = self.tmp / "failing-git-bin"
        write(
            fake_bin / "git",
            "#!/usr/bin/env bash\ncase \" $* \" in\n"
            "    *\" rev-parse --show-toplevel \"*) exit 0 ;;\n"
            "    *\" diff --cached --name-only \"*) exit 74 ;;\n"
            "    *) exit 75 ;;\nesac\n",
        )
        os.chmod(fake_bin / "git", 0o755)
        result = self.run_stop(env={"PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"})
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("unable to inspect code changes; running configured checks.", result.stderr)
        self.assertEqual({"script", "command"}, self.effects())

    def test_malformed_extension_list_runs_the_checks_instead_of_skipping_them(self) -> None:
        self.commit_everything()
        for name, value in [("null", None), ("object", {"ts": True}), ("wrong item", ["ts", 7])]:
            with self.subTest(name):
                self.edit_stop_config(run_on_code_changes=True, code_change_extensions=value)
                result = self.run_stop()
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertIn("invalid code_change_extensions configuration", result.stderr)
                self.assertEqual({"script", "command"}, self.effects())

    def test_session_context_uses_hook_specific_output(self) -> None:
        result = run(
            [
                "bash",
                "-c",
                f"source {self.root}/lib/agent-hook-runtime.sh; source {self.root}/lib/claude.sh; "
                "AGENT_HOOK_EVENT=SessionStart; write_additional_context 'shared context'",
            ],
            cwd=self.project,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual({"hookEventName": "SessionStart", "additionalContext": "shared context"}, output)


class HarnessProtocolTests(unittest.TestCase):
    def test_devin_stop_failure_exits_2_with_a_block_decision(self) -> None:
        tmp = tmp_root(self)
        project = tmp / "project"
        project.mkdir()
        run(["git", "init", "-q"], cwd=project)
        write(project / "src" / "example.ts", "export const example = true;\n")
        write(project / "scripts" / "agent-stop-checks.sh", "#!/usr/bin/env bash\nprintf 'portable shared script %s\\n' \"${1:-}\" >&2\n")

        def edit(plan: dict) -> None:
            event(plan, "Stop")["commands"] = [
                {"label": "block", "command": "printf 'must block\\n' >&2; exit 7", "cwd": "."}
            ]

        scaffold_harness("devin", project, plan_with("devin", tmp, edit))
        result = run(
            ["bash", str(project / "hooks" / "stop" / "devin.sh")],
            cwd=project,
            input_text=STOP_PAYLOAD,
            env={"DEVIN_PROJECT_DIR": str(project)},
        )
        self.assertEqual(2, result.returncode, result.stderr)
        self.assertIn("must block", result.stderr)
        self.assertIn('"decision": "block"', result.stdout)

    def test_copilot_failures_become_deny_decisions_and_custom_hooks_survive(self) -> None:
        tmp = tmp_root(self)
        project = tmp / "project"
        write(
            project / ".github" / "hooks" / "custom.json",
            json.dumps({"version": 1, "hooks": {"sessionStart": [{"type": "command", "bash": "echo custom", "cwd": "."}]}}),
        )
        write(project / "scripts" / "agent-stop-checks.sh", "#!/usr/bin/env bash\nexit 0\n")

        def edit(plan: dict) -> None:
            plan["enabled_events"].append(
                {
                    "name": "preToolUse",
                    "matcher": "bash|edit|create",
                    "timeoutSec": 15,
                    "block_on_failure": True,
                    "scripts": [],
                    "commands": [{"label": "deny", "command": "printf 'pretool policy failed\\n' >&2; exit 7", "cwd": "."}],
                }
            )
            plan["enabled_events"].append(
                {
                    "name": "permissionRequest",
                    "matcher": "bash",
                    "timeoutSec": 10,
                    "block_on_failure": True,
                    "scripts": [],
                    "commands": [{"label": "deny", "command": "printf 'permission policy failed\\n' >&2; exit 9", "cwd": "."}],
                }
            )

        scaffold_harness("copilot", project, plan_with("copilot", tmp, edit))
        hooks = load_json(project / ".github" / "hooks" / "copilot-hooks.json")
        self.assertEqual(1, hooks["version"])
        self.assertIn(".github/copilot/hooks/generated", json.dumps(hooks["hooks"]))
        self.assertTrue((project / ".github" / "hooks" / "custom.json").exists())
        self.assertFalse((project / ".claude").exists())

        events = project / ".github" / "copilot" / "hooks" / "generated" / "events"
        payload = json.dumps(
            {"sessionId": "s1", "timestamp": 1781060000000, "cwd": str(project), "toolName": "bash", "toolArgs": {"command": "rm -rf dist"}}
        )
        env = {"GITHUB_WORKSPACE": str(project)}

        pre = run(["bash", str(events / "pre-tool-use.sh")], cwd=project, input_text=payload, env=env)
        self.assertEqual(0, pre.returncode, pre.stderr)
        self.assertIn("pretool policy failed", pre.stderr)
        self.assertIn('"permissionDecision":"deny"', pre.stdout)

        permission = run(["bash", str(events / "permission-request.sh")], cwd=project, input_text=payload, env=env)
        self.assertEqual(2, permission.returncode)
        self.assertIn('"behavior":"deny"', permission.stdout)

    def test_codex_scaffold_without_feature_flag_writes_hooks_json(self) -> None:
        tmp = tmp_root(self)
        project = tmp / "project"
        project.mkdir()
        run(["git", "init", "-q"], cwd=project)
        scaffold_harness("codex", project, SKILL / "harnesses" / "codex" / "templates" / "hook-plan.example.json")
        hooks = load_json(project / ".codex" / "hooks.json")
        self.assertIn("SessionStart", hooks["hooks"])
        self.assertNotIn("\\$(git rev-parse", json.dumps(hooks))


if __name__ == "__main__":
    unittest.main()
