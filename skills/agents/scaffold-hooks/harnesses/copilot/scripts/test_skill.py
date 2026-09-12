#!/usr/bin/env python3
"""
test_skill.py

Lightweight checks for the copilot harness component of scaffold-hooks.
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
    "sessionStart",
    "sessionEnd",
    "userPromptSubmitted",
    "preToolUse",
    "postToolUse",
    "postToolUseFailure",
    "agentStop",
    "subagentStart",
    "subagentStop",
    "errorOccurred",
    "preCompact",
    "permissionRequest",
    "notification",
}
REQUIRED_EXECUTABLES = [
    "scripts/audit_project.sh",
    "scripts/merge_hooks_file.sh",
    "scripts/render_hooks_readme.sh",
    "scripts/scaffold_hooks.sh",
    "scripts/verify_docs.py",
]


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


def readable_stub_errors(script_path: Path) -> list[str]:
    content = script_path.read_text(encoding="utf-8")
    required_snippets = [
        "How this script is organized:",
        "Safe editing rule:",
        "handle_event()",
        "Project-specific logic belongs here.",
        "run_configured_event_effects",
        "BLOCK_ON_FAILURE",
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
        "hook_tool_name()",
        "deny_pre_tool_use()",
        "deny_permission_request()",
        "block_agent_stop()",
        "copilot_project_root()",
        "run_project_command()",
        "run_project_script()",
        "validate_configured_items_json()",
        "run_configured_scripts()",
        "run_configured_event_effects()",
        "handle_configured_failure()",
        "preToolUse",
        "permissionRequest",
    ]
    return [
        f"common.sh is missing helper marker: {snippet}"
        for snippet in required_snippets
        if snippet not in content
    ]


def test_skill(skill_path: Path) -> dict:
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
    if plan_template.get("hooks_target") != ".github/hooks/copilot-hooks.json":
        results["errors"].append("Plan template must target .github/hooks/copilot-hooks.json")
        results["passed"] = False
    for enabled_event in plan_template.get("enabled_events", []):
        if enabled_event.get("name") not in EXPECTED_EVENT_NAMES:
            results["errors"].append(
                f"Plan template references unknown event: {enabled_event.get('name')}"
            )
            results["passed"] = False

    skill_md = (skill_path / "PLAYBOOK.md").read_text(encoding="utf-8")
    for snippet in [
        "## Progressive Maintainer Drift Check",
        "Live-fetch the three official GitHub Copilot hook docs",
        ".github/hooks/copilot-hooks.json",
        "preToolUse` denies through stdout JSON",
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
        (project / ".github" / "hooks").mkdir(parents=True)
        (project / ".github" / "hooks" / "custom.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "disableAllHooks": False,
                    "hooks": {
                        "sessionStart": [
                            {
                                "type": "command",
                                "bash": "echo custom",
                                "cwd": ".",
                            }
                        ]
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        temp_plan = tmp / "hook-plan.json"
        plan_data = load_json(skill_path / "templates" / "hook-plan.example.json")
        for enabled_event in plan_data.get("enabled_events", []):
            if enabled_event.get("name") == "preToolUse":
                enabled_event["commands"] = [
                    {
                        "label": "intentional preToolUse denial",
                        "command": "printf 'pretool policy failed\\n' >&2; exit 7",
                        "cwd": ".",
                    }
                ]
            if enabled_event.get("name") == "agentStop":
                enabled_event["scripts"] = [
                    {
                        "label": "shared stop checks",
                        "path": "scripts/agent-stop-checks.sh",
                        "args": ["copilot"],
                        "cwd": ".",
                    }
                ]
                enabled_event["commands"] = [
                    {
                        "label": "intentional stop block",
                        "command": "printf 'stop check failed\\n' >&2; exit 8",
                        "cwd": ".",
                    }
                ]
        plan_data["enabled_events"].append(
            {
                "name": "permissionRequest",
                "matcher": "bash",
                "timeoutSec": 10,
                "block_on_failure": True,
                "scripts": [],
                "commands": [
                    {
                        "label": "intentional permission deny",
                        "command": "printf 'permission policy failed\\n' >&2; exit 9",
                        "cwd": ".",
                    }
                ],
            }
        )
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
            manifest_script_names = [
                event["script_name"] for event in load_json(skill_path / "assets" / "hook-events.json")["events"]
            ]
            expected_files = [
                project / ".github" / "hooks" / "copilot-hooks.json",
                project / ".github" / "copilot" / "hooks" / "README.md",
                project / ".github" / "copilot" / "hooks" / "generated" / "manifest.json",
                project / ".github" / "copilot" / "hooks" / "generated" / "hooks.generated.json",
                project / ".github" / "copilot" / "hooks" / "generated" / "lib" / "common.sh",
            ]
            expected_files.extend(
                project / ".github" / "copilot" / "hooks" / "generated" / "events" / script_name
                for script_name in manifest_script_names
            )
            if all(path.exists() for path in expected_files):
                hooks_file = load_json(project / ".github" / "hooks" / "copilot-hooks.json")
                hooks = hooks_file.get("hooks", {})
                command_blob = json.dumps(hooks)
                if hooks_file.get("version") != 1:
                    results["errors"].append("copilot-hooks.json must contain version: 1")
                    results["passed"] = False
                elif "preToolUse" not in hooks or "permissionRequest" not in hooks or "agentStop" not in hooks:
                    results["errors"].append("generated hook file missing expected enabled events")
                    results["passed"] = False
                elif ".github/copilot/hooks/generated" not in command_blob:
                    results["errors"].append("generated hook entries do not point to the managed root")
                    results["passed"] = False
                elif (project / ".claude").exists():
                    results["errors"].append("scaffold created .claude config even though target should be .github/hooks")
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
        generated_root = project / ".github" / "copilot" / "hooks" / "generated"
        for rel_path in [
            "events/pre-tool-use.sh",
            "events/permission-request.sh",
            "events/agent-stop.sh",
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
        pre_tool_script = generated_root / "events" / "pre-tool-use.sh"
        if pre_tool_script.exists():
            pre_tool_payload = json.dumps(
                {
                    "sessionId": "s1",
                    "timestamp": 1781060000000,
                    "cwd": str(project),
                    "toolName": "bash",
                    "toolArgs": {"command": "rm -rf dist"},
                }
            )
            pre_tool_proc = run(
                ["bash", str(pre_tool_script)],
                cwd=project,
                input_text=pre_tool_payload,
                env={"GITHUB_WORKSPACE": str(project)},
            )
            if (
                pre_tool_proc.returncode == 0
                and "pretool policy failed" in pre_tool_proc.stderr
                and '"permissionDecision":"deny"' in pre_tool_proc.stdout
            ):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append(
                    "generated preToolUse hook did not translate failure into permissionDecision deny JSON with exit 0"
                )
                results["passed"] = False
        else:
            results["errors"].append("generated preToolUse hook missing before decision check")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        permission_script = generated_root / "events" / "permission-request.sh"
        if permission_script.exists():
            permission_payload = json.dumps(
                {
                    "sessionId": "s1",
                    "timestamp": 1781060000000,
                    "cwd": str(project),
                    "toolName": "bash",
                    "toolArgs": {"command": "touch file"},
                }
            )
            permission_proc = run(
                ["bash", str(permission_script)],
                cwd=project,
                input_text=permission_payload,
                env={"GITHUB_WORKSPACE": str(project)},
            )
            if (
                permission_proc.returncode == 2
                and "permission policy failed" in permission_proc.stderr
                and '"behavior":"deny"' in permission_proc.stdout
            ):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append(
                    "generated permissionRequest hook did not translate failure into exit code 2 with behavior deny JSON"
                )
                results["passed"] = False
        else:
            results["errors"].append("generated permissionRequest hook missing before exit-code-2 check")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        agent_stop_script = generated_root / "events" / "agent-stop.sh"
        if agent_stop_script.exists():
            original_agent_stop = agent_stop_script.read_text(encoding="utf-8")
            invalid_agent_stop, replacement_count = re.subn(
                r"^PROJECT_COMMANDS_JSON=.*$",
                "PROJECT_COMMANDS_JSON='null'",
                original_agent_stop,
                count=1,
                flags=re.MULTILINE,
            )
            agent_stop_script.write_text(invalid_agent_stop, encoding="utf-8")
            effect_marker.unlink(missing_ok=True)
            preflight_proc = run(
                ["bash", str(agent_stop_script)],
                cwd=project,
                input_text=json.dumps(
                    {
                        "sessionId": "s1",
                        "timestamp": 1781060000000,
                        "cwd": str(project),
                    }
                ),
                env={
                    "GITHUB_WORKSPACE": str(project),
                    "SCAFFOLD_HOOK_EFFECT_MARKER": str(effect_marker),
                },
            )
            agent_stop_script.write_text(original_agent_stop, encoding="utf-8")
            if (
                replacement_count != 1
                or "invalid commands configuration" not in preflight_proc.stderr
                or effect_marker.exists()
            ):
                results["errors"].append(
                    "generated agentStop hook ran a valid script before rejecting malformed commands: "
                    f"replacement_count={replacement_count}, status={preflight_proc.returncode}, "
                    f"marker={effect_marker.exists()}, stderr={preflight_proc.stderr}"
                )
                results["passed"] = False
            else:
                results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("generated agentStop hook missing before preflight check")
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
