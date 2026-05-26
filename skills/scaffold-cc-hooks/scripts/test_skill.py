#!/usr/bin/env python3
"""
test_skill.py

Lightweight checks for scaffold-cc-hooks.

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
) -> subprocess.CompletedProcess[str]:
    """Run a command and capture output for test assertions."""
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        input=input_text,
        check=False,
        capture_output=True,
        text=True,
    )


def readable_stub_errors(script_path: Path) -> list[str]:
    """Assert generated event scripts expose a clear edit point."""
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
    """Assert generated common.sh documents the helper layer."""
    content = common_path.read_text(encoding="utf-8")
    required_snippets = [
        "require_jq()",
        "Read one value from HOOK_INPUT with jq.",
        "Hook output helpers build JSON with jq",
        "run_project_command()",
        "run_project_script()",
        "run_configured_scripts()",
        "handle_project_command_failure()",
        "This is deliberately language-agnostic.",
        "Emit additionalContext text for the next Claude turn.",
    ]
    return [
        f"common.sh is missing helper documentation: {snippet}"
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

    plan_template = load_json(skill_path / "templates" / "hook-plan.example.json")
    for enabled_event in plan_template.get("enabled_events", []):
        if enabled_event.get("name") not in EXPECTED_EVENT_NAMES:
            results["errors"].append(
                f"Plan template references unknown event: {enabled_event.get('name')}"
            )
            results["passed"] = False

    skill_md = (skill_path / "SKILL.md").read_text(encoding="utf-8")
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

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        project = tmp / "project"
        project.mkdir()
        (project / "scripts").mkdir()
        (project / "scripts" / "agent-stop-checks.sh").write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf 'portable shared script %s\\n' \"${1:-}\" >&2\n",
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
            ],
            cwd=skill_path,
        )
        if scaffold.returncode == 0:
            manifest_script_names = [
                event["script_name"] for event in load_json(skill_path / "assets" / "hook-events.json")["events"]
            ]
            expected_files = [
                project / ".claude" / "settings.json",
                project / ".claude" / "hooks" / "README.md",
                project / ".claude" / "hooks" / "generated" / "manifest.json",
                project / ".claude" / "hooks" / "generated" / "settings.generated.json",
                project / ".claude" / "hooks" / "generated" / "lib" / "common.sh",
            ]
            expected_files.extend(
                project / ".claude" / "hooks" / "generated" / "events" / script_name
                for script_name in manifest_script_names
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
        generated_root = project / ".claude" / "hooks" / "generated"
        for rel_path in [
            "events/session-start.sh",
            "events/pre-tool-use.sh",
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
        stop_script = generated_root / "events" / "stop.sh"
        if stop_script.exists():
            stop_payload = json.dumps(
                {
                    "hook_event_name": "Stop",
                    "cwd": str(project),
                    "stop_hook_active": False,
                }
            )
            stop_proc = run([str(stop_script)], cwd=project, input_text=stop_payload)
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
