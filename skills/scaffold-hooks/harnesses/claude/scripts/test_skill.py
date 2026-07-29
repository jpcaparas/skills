#!/usr/bin/env python3
"""
test_skill.py

Lightweight checks for the claude harness component of scaffold-hooks.

Usage:
    python3 test_skill.py <skill-path>

Exit codes:
    0 = all checks passed
    1 = one or more checks failed
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


EXPECTED_EVENT_NAMES = {
    "SessionStart",
    "Setup",
    "InstructionsLoaded",
    "UserPromptSubmit",
    "UserPromptExpansion",
    "PreToolUse",
    "PermissionRequest",
    "PermissionDenied",
    "PostToolUse",
    "PostToolUseFailure",
    "PostToolBatch",
    "Notification",
    "MessageDisplay",
    "SubagentStart",
    "SubagentStop",
    "TaskCreated",
    "TaskCompleted",
    "Stop",
    "StopFailure",
    "TeammateIdle",
    "ConfigChange",
    "CwdChanged",
    "FileChanged",
    "WorktreeCreate",
    "WorktreeRemove",
    "PreCompact",
    "PostCompact",
    "SessionEnd",
    "Elicitation",
    "ElicitationResult",
}
REQUIRED_EXECUTABLES = [
    "scripts/audit_project.sh",
    "scripts/check_workspace_trust.sh",
    "scripts/merge_settings.sh",
    "scripts/render_hooks_readme.sh",
    "scripts/scaffold_hooks.sh",
]


def extract_file_references(content: str) -> list[str]:
    """Extract local file references from markdown while ignoring fenced code."""
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")
    refs: list[str] = []

    for match in re.finditer(
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`", stripped
    ):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.append(path)

    for match in re.finditer(
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
        stripped,
    ):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.append(path)

    return sorted(set(refs))


def load_json(path: Path) -> dict:
    """Load JSON from disk and raise a useful error if parsing fails."""
    return json.loads(path.read_text(encoding="utf-8"))


def run(
    cmd: list[str],
    cwd: Path | None = None,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a command and capture output for test assertions."""
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


def readable_stub_errors(script_path: Path) -> list[str]:
    """Assert generated event scripts expose a clear edit point."""
    content = script_path.read_text(encoding="utf-8")
    required_snippets = [
        "How this script is organized:",
        "Safe editing rule:",
        "handle_event()",
        "run_hook_event handle_event",
        "Project-specific logic belongs here.",
        "run_configured_scripts",
        "run_configured_commands",
        "read_adapter_config",
        "config_scripts_json",
        "config_commands_json",
        'HOOK_INPUT="$(read_hook_input)"',
        'main "$@"',
    ]
    return [
        f"{script_path.name} is missing readable stub marker: {snippet}"
        for snippet in required_snippets
        if snippet not in content
    ]


def readable_common_errors(common_path: Path) -> list[str]:
    """Assert generated agent-hook-runtime.sh documents the helper layer."""
    content = common_path.read_text(encoding="utf-8")
    required_snippets = [
        "require_jq()",
        "read_adapter_config()",
        "config_collection_json()",
        "config_scripts_json()",
        "config_commands_json()",
        "validate_configured_items_json()",
        "run_project_command()",
        "run_project_script()",
        "run_configured_scripts()",
        "hook_has_code_changes()",
        "hook_should_skip_event()",
        "validate_code_change_extensions_json()",
        "preflight_configured_effects()",
        "run_hook_event()",
        'command_statuses=("${PIPESTATUS[@]}")',
        "unable to inspect code changes; running configured checks.",
    ]
    return [
        f"agent-hook-runtime.sh is missing helper marker: {snippet}"
        for snippet in required_snippets
        if snippet not in content
    ]


def test_skill(skill_path: Path) -> dict:
    """Run lightweight behavioral checks on the skill contents."""
    results = {
        "skill_name": skill_path.name,
        "tests_found": 0,
        "files_verified": {"passed": 0, "total": 0},
        "cross_references": {"passed": 0, "total": 0},
        "integration_checks": {"passed": 0, "total": 0},
        "errors": [],
        "passed": True,
    }

    # Evals live at the scaffold-hooks skill level; no per-harness evals.

    manifest = load_json(skill_path / "assets" / "hook-events.json")
    manifest_names = {event.get("name") for event in manifest.get("events", [])}
    if manifest_names != EXPECTED_EVENT_NAMES:
        missing = sorted(EXPECTED_EVENT_NAMES - manifest_names)
        unexpected = sorted(manifest_names - EXPECTED_EVENT_NAMES)
        if missing:
            results["errors"].append(f"Manifest is missing events: {', '.join(missing)}")
        if unexpected:
            results["errors"].append(f"Manifest contains unexpected events: {', '.join(unexpected)}")
        results["passed"] = False

    plan_template = load_json(skill_path / "templates" / "hook-plan.example.json")
    for enabled_event in plan_template.get("enabled_events", []):
        if enabled_event.get("name") not in EXPECTED_EVENT_NAMES:
            results["errors"].append(
                f"Plan template references unknown event: {enabled_event.get('name')}"
            )
            results["passed"] = False

    skill_md = (skill_path / "PLAYBOOK.md").read_text(encoding="utf-8")
    for snippet in [
        "## Progressive Maintainer Drift Check",
        "Live-fetch the official Claude Code docs",
        "assets/hook-events.json",
        "validators, tests, evals",
        "Do not update this skill from memory",
    ]:
        if snippet not in skill_md:
            results["errors"].append(f"PLAYBOOK.md is missing maintainer drift guidance: {snippet}")
            results["passed"] = False

    for ref in extract_file_references(skill_md):
        results["cross_references"]["total"] += 1
        if (skill_path / ref).exists():
            results["cross_references"]["passed"] += 1
        else:
            results["errors"].append(f"Cross-reference not found: {ref}")
            results["passed"] = False

    for ref_file in (skill_path / "references").glob("*.md"):
        ref_content = ref_file.read_text(encoding="utf-8")
        for ref in extract_file_references(ref_content):
            results["cross_references"]["total"] += 1
            if (skill_path / ref).exists():
                results["cross_references"]["passed"] += 1
            else:
                results["errors"].append(
                    f"Cross-reference in {ref_file.relative_to(skill_path)} not found: {ref}"
                )
                results["passed"] = False

    for rel_path in REQUIRED_EXECUTABLES:
        full_path = skill_path / rel_path
        if not os.access(full_path, os.X_OK):
            results["errors"].append(f"Script is not executable: {rel_path}")
            results["passed"] = False

    with tempfile.TemporaryDirectory(dir=skill_path) as tmpdir:
        tmp = Path(tmpdir)
        project = tmp / "project"
        project.mkdir()
        run(["git", "init", "-q"], cwd=project)
        (project / "src").mkdir()
        (project / "src" / "example.ts").write_text("export const example = true;\n", encoding="utf-8")
        (project / "scripts").mkdir()
        effect_marker = project / "configured-effect.marker"
        (project / "scripts" / "agent-stop-checks.sh").write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf 'portable shared script %s\\n' \"${1:-}\" >&2\n"
            "if [ -n \"${SCAFFOLD_HOOK_EFFECT_MARKER:-}\" ]; then\n"
            "    printf 'script\\n' >> \"$SCAFFOLD_HOOK_EFFECT_MARKER\"\n"
            "fi\n",
            encoding="utf-8",
        )
        temp_plan = tmp / "hook-plan.json"
        plan_data = load_json(skill_path / "templates" / "hook-plan.example.json")
        for enabled_event in plan_data.get("enabled_events", []):
            if enabled_event.get("name") == "Stop":
                enabled_event["scripts"] = [
                    {
                        "label": "shared stop checks",
                        "path": "scripts/agent-stop-checks.sh",
                        "args": ["claude"],
                        "cwd": ".",
                    }
                ]
                enabled_event["commands"] = [
                    {
                        "label": "portable hook command",
                        "command": (
                            "printf 'portable hook command\\n' >&2; "
                            "if [ -n \"${SCAFFOLD_HOOK_EFFECT_MARKER:-}\" ]; then "
                            "printf 'command\\n' >> \"$SCAFFOLD_HOOK_EFFECT_MARKER\"; fi"
                        ),
                        "cwd": ".",
                    }
                ]
        temp_plan.write_text(json.dumps(plan_data, indent=2) + "\n", encoding="utf-8")

        results["integration_checks"]["total"] += 1
        scaffold = run(
            [
                "bash",
                str(skill_path / "scripts" / "scaffold_hooks.sh"),
                "--project",
                str(project),
                "--plan",
                str(temp_plan),
            ],
            cwd=skill_path,
        )
        if scaffold.returncode == 0:
            event_dirs = [
                event["script_name"].removesuffix(".sh").replace("_", "-")
                for event in load_json(skill_path / "assets" / "hook-events.json")["events"]
            ]
            expected_files = [
                project / ".claude" / "settings.json",
                project / "hooks" / "README.md",
                project / "hooks" / ".state" / "claude" / "manifest.json",
                project / "hooks" / ".state" / "claude" / "settings.json",
                project / "hooks" / "lib" / "agent-hook-runtime.sh",
                project / "hooks" / "lib" / "claude.sh",
            ]
            expected_files.extend(
                path
                for event_dir in event_dirs
                for path in [
                    project / "hooks" / event_dir / "script.sh",
                    project / "hooks" / event_dir / "claude.sh",
                    project / "hooks" / event_dir / "claude.json",
                ]
            )
            if all(path.exists() for path in expected_files):
                settings = load_json(project / ".claude" / "settings.json")
                commands = [
                    hook.get("command", "")
                    for groups in settings.get("hooks", {}).values()
                    for group in groups
                    for hook in group.get("hooks", [])
                    if hook.get("type") == "command"
                ]
                quoted_commands = [
                    command for command in commands if '"$CLAUDE_PROJECT_DIR"' in command
                ]
                if quoted_commands:
                    results["errors"].append("Claude settings command path still contains embedded shell quotes")
                    results["passed"] = False
                elif "${CLAUDE_PROJECT_DIR}/hooks/stop/claude.sh" not in commands:
                    results["errors"].append("Claude Stop command did not use the unquoted project-dir form")
                    results["passed"] = False
                else:
                    results["integration_checks"]["passed"] += 1
            else:
                missing = [str(path.relative_to(project)) for path in expected_files if not path.exists()]
                results["errors"].append(f"scaffold_hooks.sh missed files: {', '.join(missing)}")
                results["passed"] = False
        else:
            results["errors"].append(f"scaffold_hooks.sh failed: {scaffold.stderr.strip()}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        readability_errors: list[str] = []
        generated_root = project / "hooks"
        for rel_path in [
            "session-start/script.sh",
            "pre-tool-use/script.sh",
            "stop/script.sh",
        ]:
            script_path = generated_root / rel_path
            if script_path.exists():
                readability_errors.extend(readable_stub_errors(script_path))
            else:
                readability_errors.append(f"generated script missing before readability check: {rel_path}")
        common_path = generated_root / "lib" / "agent-hook-runtime.sh"
        if common_path.exists():
            readability_errors.extend(readable_common_errors(common_path))
        else:
            readability_errors.append("generated agent-hook-runtime.sh missing before readability check")
        if readability_errors:
            results["errors"].extend(readability_errors)
            results["passed"] = False
        else:
            results["integration_checks"]["passed"] += 1

        results["integration_checks"]["total"] += 1
        stop_script = generated_root / "stop" / "claude.sh"
        if stop_script.exists():
            stop_payload = json.dumps(
                {
                    "hook_event_name": "Stop",
                    "cwd": str(project),
                    "stop_hook_active": False,
                }
            )
            stop_proc = run(["bash", str(stop_script)], cwd=project, input_text=stop_payload)
            if (
                stop_proc.returncode == 0
                and "portable shared script claude" in stop_proc.stderr
                and "portable hook command" in stop_proc.stderr
            ):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append(
                    "generated Stop hook did not run the configured reusable script and language-agnostic command"
                )
                results["passed"] = False
        else:
            results["errors"].append("generated Stop hook missing before command execution check")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        preflight_errors: list[str] = []
        stop_config_path = generated_root / "stop" / "claude.json"
        if stop_script.exists() and stop_config_path.exists():
            original_stop_config = load_json(stop_config_path)
            invalid_stop_config = json.loads(json.dumps(original_stop_config))
            invalid_stop_config["run_on_code_changes"] = False
            invalid_stop_config["commands"] = None
            stop_config_path.write_text(
                json.dumps(invalid_stop_config, indent=2) + "\n",
                encoding="utf-8",
            )
            effect_marker.unlink(missing_ok=True)
            preflight_payload = json.dumps(
                {
                    "hook_event_name": "Stop",
                    "cwd": str(project),
                    "stop_hook_active": False,
                }
            )
            preflight_proc = run(
                ["bash", str(stop_script)],
                cwd=project,
                input_text=preflight_payload,
                env={"SCAFFOLD_HOOK_EFFECT_MARKER": str(effect_marker)},
            )
            stop_config_path.write_text(
                json.dumps(original_stop_config, indent=2) + "\n",
                encoding="utf-8",
            )
            if (
                "invalid commands configuration" not in preflight_proc.stderr
                or effect_marker.exists()
            ):
                preflight_errors.append(
                    f"status={preflight_proc.returncode}, marker={effect_marker.exists()}, "
                    f"stderr={preflight_proc.stderr}"
                )
        else:
            preflight_errors.append("generated Stop hook or config is missing")

        if preflight_errors:
            results["errors"].append(
                "malformed commands ran a valid configured script before rejection: "
                + " | ".join(preflight_errors)
            )
            results["passed"] = False
        else:
            results["integration_checks"]["passed"] += 1

        results["integration_checks"]["total"] += 1
        if stop_script.exists():
            effect_marker.unlink(missing_ok=True)
            active_payload = json.dumps(
                {
                    "hook_event_name": "Stop",
                    "cwd": str(project),
                    "stop_hook_active": True,
                }
            )
            active_proc = run(
                ["bash", str(stop_script)],
                cwd=project,
                input_text=active_payload,
                env={"SCAFFOLD_HOOK_EFFECT_MARKER": str(effect_marker)},
            )
            if (
                active_proc.returncode == 0
                and "portable shared script claude" not in active_proc.stderr
                and "portable hook command" not in active_proc.stderr
                and not effect_marker.exists()
            ):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("generated Stop hook did not skip when stop_hook_active=true")
                results["passed"] = False
        else:
            results["errors"].append("generated Stop hook missing before active-stop skip check")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        subagent_guard_errors: list[str] = []
        subagent_stop_script = generated_root / "subagent-stop" / "claude.sh"
        subagent_stop_config_path = generated_root / "subagent-stop" / "claude.json"
        if (
            subagent_stop_script.exists()
            and subagent_stop_config_path.exists()
            and stop_config_path.exists()
        ):
            original_subagent_config = load_json(subagent_stop_config_path)
            guarded_subagent_config = json.loads(json.dumps(original_subagent_config))
            stop_effect_config = load_json(stop_config_path)
            guarded_subagent_config["scripts"] = stop_effect_config["scripts"]
            guarded_subagent_config["commands"] = stop_effect_config["commands"]
            guarded_subagent_config["run_on_code_changes"] = False
            subagent_stop_config_path.write_text(
                json.dumps(guarded_subagent_config, indent=2) + "\n",
                encoding="utf-8",
            )
            effect_marker.unlink(missing_ok=True)
            subagent_guard_proc = run(
                ["bash", str(subagent_stop_script)],
                cwd=project,
                input_text=json.dumps(
                    {
                        "hook_event_name": "SubagentStop",
                        "cwd": str(project),
                        "stop_hook_active": True,
                    }
                ),
                env={"SCAFFOLD_HOOK_EFFECT_MARKER": str(effect_marker)},
            )
            subagent_stop_config_path.write_text(
                json.dumps(original_subagent_config, indent=2) + "\n",
                encoding="utf-8",
            )
            if (
                subagent_guard_proc.returncode != 0
                or effect_marker.exists()
                or "portable shared script claude" in subagent_guard_proc.stderr
                or "portable hook command" in subagent_guard_proc.stderr
            ):
                subagent_guard_errors.append(
                    f"status={subagent_guard_proc.returncode}, marker={effect_marker.exists()}, "
                    f"stderr={subagent_guard_proc.stderr}"
                )
        else:
            subagent_guard_errors.append("generated SubagentStop hook or config is missing")

        if subagent_guard_errors:
            results["errors"].append(
                "generated SubagentStop entry path bypassed the active-stop guard: "
                + " | ".join(subagent_guard_errors)
            )
            results["passed"] = False
        else:
            results["integration_checks"]["passed"] += 1

        run(["git", "add", "."], cwd=project)
        run(
            [
                "git",
                "-c",
                "user.name=scaffold-hooks-test",
                "-c",
                "user.email=scaffold-hooks-test@example.com",
                "commit",
                "-qm",
                "fixture",
            ],
            cwd=project,
        )

        results["integration_checks"]["total"] += 1
        if stop_script.exists():
            clean_payload = json.dumps(
                {
                    "hook_event_name": "Stop",
                    "cwd": str(project),
                    "stop_hook_active": False,
                }
            )
            clean_proc = run(["bash", str(stop_script)], cwd=project, input_text=clean_payload)
            if (
                clean_proc.returncode == 0
                and "portable shared script claude" not in clean_proc.stderr
                and "portable hook command" not in clean_proc.stderr
            ):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("generated Stop hook did not skip when no code changes are present")
                results["passed"] = False
        else:
            results["errors"].append("generated Stop hook missing before no-change skip check")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        git_failure_errors: list[str] = []
        if stop_script.exists():
            failing_git_bin = tmp / "failing-git-bin"
            failing_git_bin.mkdir()
            failing_git = failing_git_bin / "git"
            failing_git.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "case \" $* \" in\n"
                "    *\" rev-parse --show-toplevel \"*) exit 0 ;;\n"
                "    *\" diff --cached --name-only \"*) exit 74 ;;\n"
                "    *) exit 75 ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            failing_git.chmod(0o755)
            effect_marker.unlink(missing_ok=True)
            git_failure_proc = run(
                ["bash", str(stop_script)],
                cwd=project,
                input_text=clean_payload,
                env={
                    "PATH": f"{failing_git_bin}{os.pathsep}{os.environ.get('PATH', '')}",
                    "SCAFFOLD_HOOK_EFFECT_MARKER": str(effect_marker),
                },
            )
            marker_effects = (
                effect_marker.read_text(encoding="utf-8").splitlines()
                if effect_marker.exists()
                else []
            )
            if (
                git_failure_proc.returncode != 0
                or "unable to inspect code changes; running configured checks."
                not in git_failure_proc.stderr
                or set(marker_effects) != {"script", "command"}
            ):
                git_failure_errors.append(
                    f"status={git_failure_proc.returncode}, effects={marker_effects}, "
                    f"stderr={git_failure_proc.stderr}"
                )
        else:
            git_failure_errors.append("generated Stop hook is missing")

        if git_failure_errors:
            results["errors"].append(
                "Git enumeration failure suppressed configured Stop checks: "
                + " | ".join(git_failure_errors)
            )
            results["passed"] = False
        else:
            results["integration_checks"]["passed"] += 1

        results["integration_checks"]["total"] += 1
        malformed_extension_errors: list[str] = []
        stop_config_path = generated_root / "stop" / "claude.json"
        if stop_script.exists() and stop_config_path.exists():
            original_stop_config = load_json(stop_config_path)
            malformed_extensions = [
                ("null", None),
                ("object", {"ts": True}),
                ("wrong item", ["ts", 7]),
            ]
            for case_name, invalid_extensions in malformed_extensions:
                invalid_stop_config = json.loads(json.dumps(original_stop_config))
                invalid_stop_config["run_on_code_changes"] = True
                invalid_stop_config["code_change_extensions"] = invalid_extensions
                stop_config_path.write_text(
                    json.dumps(invalid_stop_config, indent=2) + "\n",
                    encoding="utf-8",
                )
                effect_marker.unlink(missing_ok=True)
                malformed_proc = run(
                    ["bash", str(stop_script)],
                    cwd=project,
                    input_text=clean_payload,
                    env={"SCAFFOLD_HOOK_EFFECT_MARKER": str(effect_marker)},
                )
                marker_effects = (
                    effect_marker.read_text(encoding="utf-8").splitlines()
                    if effect_marker.exists()
                    else []
                )
                if (
                    malformed_proc.returncode != 0
                    or "invalid code_change_extensions configuration" not in malformed_proc.stderr
                    or set(marker_effects) != {"script", "command"}
                ):
                    malformed_extension_errors.append(
                        f"{case_name}: status={malformed_proc.returncode}, "
                        f"effects={marker_effects}, stderr={malformed_proc.stderr}"
                    )
            stop_config_path.write_text(
                json.dumps(original_stop_config, indent=2) + "\n",
                encoding="utf-8",
            )
        else:
            malformed_extension_errors.append("generated Stop hook or config is missing")

        if malformed_extension_errors:
            results["errors"].append(
                "malformed code_change_extensions suppressed configured checks: "
                + " | ".join(malformed_extension_errors)
            )
            results["passed"] = False
        else:
            results["integration_checks"]["passed"] += 1

        results["integration_checks"]["total"] += 1
        claude_lib = generated_root / "lib" / "claude.sh"
        runtime_lib = generated_root / "lib" / "agent-hook-runtime.sh"
        context_proc = run(
            [
                "bash",
                "-c",
                f"source {runtime_lib}; source {claude_lib}; AGENT_HOOK_EVENT=SessionStart; write_additional_context 'shared context'",
            ],
            cwd=project,
        )
        if context_proc.returncode == 0:
            context_json = json.loads(context_proc.stdout)
            output = context_json.get("hookSpecificOutput", {})
            if (
                output.get("hookEventName") == "SessionStart"
                and output.get("additionalContext") == "shared context"
            ):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("Claude write_additional_context did not emit hookSpecificOutput")
                results["passed"] = False
        else:
            results["errors"].append(f"Claude write_additional_context failed: {context_proc.stderr.strip()}")
            results["passed"] = False

    return results


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1

    skill_path = Path(sys.argv[1]).resolve()
    if not skill_path.is_dir():
        print(f"Error: '{skill_path}' is not a directory", file=sys.stderr)
        return 1

    results = test_skill(skill_path)

    print(f"Skill: {results['skill_name']}")
    print(f"Tests found: {results['tests_found']}")
    print(
        f"Files verified: {results['files_verified']['passed']}/"
        f"{results['files_verified']['total']}"
    )
    print(
        f"Cross-references checked: {results['cross_references']['passed']}/"
        f"{results['cross_references']['total']}"
    )
    print(
        f"Integration checks: {results['integration_checks']['passed']}/"
        f"{results['integration_checks']['total']}"
    )

    if results["errors"]:
        print(f"\nIssues ({len(results['errors'])}):")
        for error in results["errors"]:
            print(f"  - {error}")

    print()
    print("PASS: all checks passed" if results["passed"] else "FAIL: one or more checks failed")
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
