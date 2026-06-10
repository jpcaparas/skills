#!/usr/bin/env python3
"""
test_skill.py

Lightweight checks plus temp-project integration tests for scaffold-codex-hooks.
"""

from __future__ import annotations

import json
import os
import py_compile
import re
import subprocess
import sys
import tempfile
from pathlib import Path


EXPECTED_EVENT_NAMES = {
    "SessionStart",
    "SubagentStart",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PreCompact",
    "PostCompact",
    "UserPromptSubmit",
    "SubagentStop",
    "Stop",
}
BASH_SCRIPTS = [
    "scripts/audit_project.sh",
    "scripts/merge_hooks_json.sh",
    "scripts/render_hooks_readme.sh",
    "scripts/scaffold_hooks.sh",
]
PYTHON_SCRIPTS = [
    "scripts/check_hooks_feature.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
]
ESCAPED_GIT_ROOT = r"\$(git rev-parse --show-toplevel)"


def extract_file_references(content: str) -> list[str]:
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
    return json.loads(path.read_text(encoding="utf-8"))


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def iter_hook_commands(hooks_data: dict) -> list[str]:
    commands: list[str] = []

    for groups in hooks_data.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                command = hook.get("command")
                if isinstance(command, str):
                    commands.append(command)

    return commands


def first_hook_command(hooks_data: dict, event_name: str) -> str | None:
    event_groups = hooks_data.get("hooks", {}).get(event_name, [])
    for group in event_groups:
        for hook in group.get("hooks", []):
            command = hook.get("command")
            if isinstance(command, str) and command:
                return command

    return None


def readable_stub_errors(script_path: Path) -> list[str]:
    content = script_path.read_text(encoding="utf-8")
    required_snippets = [
        "How this script is organized:",
        "Safe editing rule:",
        "handle_event()",
        "Project-specific logic belongs here.",
        "run_configured_scripts",
        "run_configured_commands",
        "PROJECT_SCRIPTS_JSON",
        "PROJECT_COMMANDS_JSON",
        'HOOK_INPUT="$(read_hook_input)"',
        'main "$@"',
    ]
    return [
        f"{script_path.name} is missing readable stub marker: {snippet}"
        for snippet in required_snippets
        if snippet not in content
    ]


def readable_common_errors(common_path: Path) -> list[str]:
    content = common_path.read_text(encoding="utf-8")
    required_snippets = [
        "require_jq()",
        "Read one value from HOOK_INPUT with jq.",
        "Hook output helpers build JSON with jq",
        "allow_pre_tool_use_with_updated_input()",
        "run_project_command()",
        "run_project_script()",
        "run_configured_scripts()",
        "handle_project_command_failure()",
        "This is deliberately language-agnostic.",
        "Some hook contracts treat exit code 2 plus stderr as a block signal.",
    ]
    return [
        f"common.sh is missing helper documentation: {snippet}"
        for snippet in required_snippets
        if snippet not in content
    ]


def test_skill(skill_path: Path) -> dict:
    results = {
        "skill_name": skill_path.name,
        "tests_found": 0,
        "files_verified": {"passed": 0, "total": 0},
        "cross_references": {"passed": 0, "total": 0},
        "syntax_checks": {"passed": 0, "total": 0},
        "integration_checks": {"passed": 0, "total": 0},
        "errors": [],
        "passed": True,
    }

    evals_path = skill_path / "evals" / "evals.json"
    if not evals_path.is_file():
        results["errors"].append("evals/evals.json not found")
        results["passed"] = False
    else:
        evals_data = load_json(evals_path)
        evals_list = evals_data.get("evals", [])
        results["tests_found"] = len(evals_list)
        for eval_item in evals_list:
            for rel_path in eval_item.get("files", []):
                results["files_verified"]["total"] += 1
                if (skill_path / rel_path).exists():
                    results["files_verified"]["passed"] += 1
                else:
                    results["errors"].append(f"Eval referenced file not found: {rel_path}")
                    results["passed"] = False

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

    skill_md = (skill_path / "SKILL.md").read_text(encoding="utf-8")
    for snippet in [
        "## Progressive Maintainer Drift Check",
        "Live-fetch the official Codex hook docs",
        "generated schemas, and runtime source",
        "validators, tests, evals",
        "Do not update this skill from memory",
    ]:
        if snippet not in skill_md:
            results["errors"].append(f"SKILL.md is missing maintainer drift guidance: {snippet}")
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

    for rel_path in BASH_SCRIPTS:
        results["syntax_checks"]["total"] += 1
        proc = run(["bash", "-n", str(skill_path / rel_path)])
        if proc.returncode == 0:
            results["syntax_checks"]["passed"] += 1
        else:
            results["errors"].append(f"bash -n failed for {rel_path}: {proc.stderr.strip()}")
            results["passed"] = False

    for rel_path in PYTHON_SCRIPTS:
        results["syntax_checks"]["total"] += 1
        try:
            py_compile.compile(str(skill_path / rel_path), doraise=True)
            results["syntax_checks"]["passed"] += 1
        except py_compile.PyCompileError as exc:
            results["errors"].append(f"Python compile failed for {rel_path}: {exc.msg}")
            results["passed"] = False

    with tempfile.TemporaryDirectory(dir=skill_path) as tmpdir:
        tmp = Path(tmpdir)
        home = tmp / "home"
        project = tmp / "project"
        home.mkdir()
        project.mkdir()
        (home / ".codex").mkdir()
        (home / ".codex" / "config.toml").write_text("", encoding="utf-8")
        (project / "package.json").write_text(
            json.dumps(
                {
                    "name": "fixture-project",
                    "scripts": {
                        "lint": "echo lint",
                        "test": "echo test"
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (project / ".envrc").write_text("layout node\n", encoding="utf-8")
        (project / "scripts").mkdir()
        (project / "scripts" / "agent-session-context.sh").write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf 'portable shared script %s\\n' \"${1:-}\" >&2\n",
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["HOME"] = str(home)

        run(["git", "init"], cwd=project, env=env)

        results["integration_checks"]["total"] += 1
        audit = run(["bash", str(skill_path / "scripts" / "audit_project.sh"), str(project)], cwd=skill_path, env=env)
        if audit.returncode == 0:
            audit_data = json.loads(audit.stdout)
            if audit_data["codex"]["recommended_feature_scope"] == "project":
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("audit_project.sh did not recommend project feature scope for a git repo")
                results["passed"] = False
        else:
            results["errors"].append(f"audit_project.sh failed: {audit.stderr.strip()}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        feature_before = run(
            [
                "python3",
                str(skill_path / "scripts" / "check_hooks_feature.py"),
                "--project",
                str(project),
                "--home",
                str(home),
                "--json",
            ],
            cwd=skill_path,
            env=env,
        )
        if feature_before.returncode == 0:
            data = json.loads(feature_before.stdout)
            default_enabled = (
                data["status"] == "enabled"
                and data.get("user_explicit") is not True
                and data.get("project_explicit") is not True
            )
            if data["status"] in {"disabled", "unknown"} or default_enabled:
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("check_hooks_feature.py reported hooks enabled before any setup")
                results["passed"] = False
        else:
            results["errors"].append(f"check_hooks_feature.py failed before enable: {feature_before.stderr.strip()}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        feature_user = run(
            [
                "python3",
                str(skill_path / "scripts" / "check_hooks_feature.py"),
                "--project",
                str(project),
                "--home",
                str(home),
                "--enable",
                "--scope",
                "user",
                "--json",
            ],
            cwd=skill_path,
            env=env,
        )
        if feature_user.returncode == 0:
            data = json.loads(feature_user.stdout)
            warnings = data.get("warnings", [])
            inspection_unavailable = any(
                "codex binary not found" in warning
                or "failed to inspect effective feature state" in warning
                for warning in warnings
            )
            inspection_mismatch_reported = any(
                "effective feature is still off" in warning
                for warning in warnings
            )
            if data["user_explicit"] is True and (
                data["effective"] is True
                or (data["effective"] is None and inspection_unavailable)
                or (data["effective"] is False and inspection_mismatch_reported)
            ):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("user-scope feature enable did not become effective")
                results["passed"] = False
        else:
            results["errors"].append(f"check_hooks_feature.py failed for user enable: {feature_user.stderr.strip()}")
            results["passed"] = False

        temp_plan = tmp / "plan.json"
        plan_data = load_json(skill_path / "templates" / "hook-plan.example.json")
        plan_data["feature_scope"] = "user"
        for enabled_event in plan_data.get("enabled_events", []):
            if enabled_event.get("name") == "SessionStart":
                enabled_event["scripts"] = [
                    {
                        "label": "shared session context",
                        "path": "scripts/agent-session-context.sh",
                        "args": ["codex"],
                        "cwd": ".",
                    }
                ]
                enabled_event["commands"] = [
                    {
                        "label": "portable hook command",
                        "command": "printf 'portable hook command\\n' >&2",
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
                "--ensure-feature",
                "user",
                "--home",
                str(home),
            ],
            cwd=skill_path,
            env=env,
        )
        if scaffold.returncode == 0:
            expected_files = [
                project / ".codex" / "hooks.json",
                project / ".codex" / "hooks" / "README.md",
                project / ".codex" / "hooks" / "generated" / "manifest.json",
                project / ".codex" / "hooks" / "generated" / "hooks.generated.json",
                project / ".codex" / "hooks" / "generated" / "lib" / "common.sh",
            ]
            expected_files.extend(
                project / ".codex" / "hooks" / "generated" / "events" / name
                for name in [
                    "session_start.sh",
                    "subagent_start.sh",
                    "pre_tool_use.sh",
                    "permission_request.sh",
                    "post_tool_use.sh",
                    "pre_compact.sh",
                    "post_compact.sh",
                    "user_prompt_submit.sh",
                    "subagent_stop.sh",
                    "stop.sh",
                ]
            )
            if all(path.exists() for path in expected_files):
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
        generated_root = project / ".codex" / "hooks" / "generated"
        for rel_path in [
            "events/session_start.sh",
            "events/pre_tool_use.sh",
            "events/stop.sh",
        ]:
            script_path = generated_root / rel_path
            if script_path.exists():
                readability_errors.extend(readable_stub_errors(script_path))
            else:
                readability_errors.append(f"generated script missing before readability check: {rel_path}")
        common_path = generated_root / "lib" / "common.sh"
        if common_path.exists():
            readability_errors.extend(readable_common_errors(common_path))
        else:
            readability_errors.append("generated common.sh missing before readability check")
        if readability_errors:
            results["errors"].extend(readability_errors)
            results["passed"] = False
        else:
            results["integration_checks"]["passed"] += 1

        results["integration_checks"]["total"] += 1
        hooks_json_path = project / ".codex" / "hooks.json"
        generated_fragment_path = project / ".codex" / "hooks" / "generated" / "hooks.generated.json"
        generated_config_errors: list[str] = []
        for config_path in [hooks_json_path, generated_fragment_path]:
            if not config_path.exists():
                generated_config_errors.append(
                    f"{config_path.relative_to(project)} was not generated"
                )
                continue
            hooks_data = load_json(config_path)
            escaped_commands = [
                command for command in iter_hook_commands(hooks_data) if ESCAPED_GIT_ROOT in command
            ]
            if escaped_commands:
                generated_config_errors.append(
                    f"{config_path.relative_to(project)} contains escaped git-root command substitution"
                )

        if generated_config_errors:
            results["errors"].extend(generated_config_errors)
            results["passed"] = False
        else:
            results["integration_checks"]["passed"] += 1

        results["integration_checks"]["total"] += 1
        if hooks_json_path.exists():
            hooks_data = load_json(hooks_json_path)
            session_command = first_hook_command(hooks_data, "SessionStart")
            pre_tool_use_command = first_hook_command(hooks_data, "PreToolUse")
            if not session_command:
                results["errors"].append("SessionStart command was not generated in hooks.json")
                results["passed"] = False
            elif not pre_tool_use_command:
                results["errors"].append("PreToolUse command was not generated in hooks.json")
                results["passed"] = False
            else:
                command_procs = [
                    (
                        "SessionStart",
                        session_command,
                        json.dumps({"source": "startup", "cwd": str(project)}),
                    ),
                    (
                        "PreToolUse",
                        pre_tool_use_command,
                        json.dumps(
                            {
                                "tool_input": {"command": "pwd"},
                                "cwd": str(project),
                            }
                        ),
                    ),
                ]
                command_errors: list[str] = []
                for event_name, command, payload in command_procs:
                    proc = subprocess.run(
                        command,
                        cwd=str(project),
                        env=env,
                        input=payload,
                        check=False,
                        capture_output=True,
                        text=True,
                        shell=True,
                    )
                    if proc.returncode != 0:
                        command_errors.append(
                            f"generated {event_name} command did not execute cleanly: "
                            f"{proc.stderr.strip() or proc.stdout.strip() or 'unknown error'}"
                        )
                    if event_name == "SessionStart" and (
                        "portable shared script codex" not in proc.stderr
                        or "portable hook command" not in proc.stderr
                    ):
                        command_errors.append(
                            "generated SessionStart command did not run the configured reusable script and language-agnostic command"
                        )
                if command_errors:
                    results["errors"].extend(command_errors)
                    results["passed"] = False
                else:
                    results["integration_checks"]["passed"] += 1

        results["integration_checks"]["total"] += 1
        if hooks_json_path.exists():
            hooks_data = load_json(hooks_json_path)
            custom_group = {
                "matcher": "startup",
                "hooks": [
                    {
                        "type": "command",
                        "command": "echo custom-session-start"
                    }
                ]
            }
            hooks_data.setdefault("hooks", {}).setdefault("SessionStart", []).append(custom_group)
            hooks_json_path.write_text(json.dumps(hooks_data, indent=2) + "\n", encoding="utf-8")

            scaffold_again = run(
                [
                    "bash",
                    str(skill_path / "scripts" / "scaffold_hooks.sh"),
                    "--project",
                    str(project),
                    "--plan",
                    str(temp_plan),
                    "--ensure-feature",
                    "user",
                    "--home",
                    str(home),
                ],
                cwd=skill_path,
                env=env,
            )
            if scaffold_again.returncode == 0:
                merged_hooks = load_json(hooks_json_path)
                session_groups = merged_hooks.get("hooks", {}).get("SessionStart", [])
                if any(
                    hook.get("command") == "echo custom-session-start"
                    for group in session_groups
                    for hook in group.get("hooks", [])
                ):
                    results["integration_checks"]["passed"] += 1
                else:
                    results["errors"].append("additive scaffold removed a custom SessionStart hook")
                    results["passed"] = False
            else:
                results["errors"].append(f"second scaffold run failed: {scaffold_again.stderr.strip()}")
                results["passed"] = False
        else:
            results["errors"].append("hooks.json was not created before additive re-run test")
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
        f"Syntax checks: {results['syntax_checks']['passed']}/"
        f"{results['syntax_checks']['total']}"
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
