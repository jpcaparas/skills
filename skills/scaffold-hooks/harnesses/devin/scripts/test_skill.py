#!/usr/bin/env python3
"""
test_skill.py

Lightweight checks for the devin harness component of scaffold-hooks.

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
    "PreToolUse",
    "PostToolUse",
    "PermissionRequest",
    "UserPromptSubmit",
    "Stop",
    "PostCompaction",
    "SessionStart",
    "SessionEnd",
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
    content = common_path.read_text(encoding="utf-8")
    required_snippets = [
        "require_jq()",
        "read_adapter_config()",
        "config_scripts_json()",
        "config_commands_json()",
        "run_project_command()",
        "run_project_script()",
        "run_configured_scripts()",
    ]
    return [
        f"agent-hook-runtime.sh is missing helper marker: {snippet}"
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
    if plan_template.get("hooks_target") != ".devin/hooks.v1.json":
        results["errors"].append("Plan template must target .devin/hooks.v1.json")
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
        "Live-fetch both official Devin docs",
        ".devin/hooks.v1.json",
        "exit code `2`",
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
                enabled_event["commands"] = [
                    {
                        "label": "intentional blocking command",
                        "command": "printf 'must block\\n' >&2; exit 7",
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
                project / ".devin" / "hooks.v1.json",
                project / "hooks" / "README.md",
                project / "hooks" / ".state" / "devin" / "manifest.json",
                project / "hooks" / ".state" / "devin" / "hooks.v1.json",
                project / "hooks" / "lib" / "agent-hook-runtime.sh",
                project / "hooks" / "lib" / "devin.sh",
            ]
            expected_files.extend(
                path
                for event_dir in event_dirs
                for path in [
                    project / "hooks" / event_dir / "script.sh",
                    project / "hooks" / event_dir / "devin.sh",
                    project / "hooks" / event_dir / "devin.json",
                ]
            )
            if all(path.exists() for path in expected_files):
                hooks_file = load_json(project / ".devin" / "hooks.v1.json")
                if "hooks" in hooks_file:
                    results["errors"].append(".devin/hooks.v1.json must not contain a top-level hooks wrapper")
                    results["passed"] = False
                elif (project / ".claude").exists():
                    results["errors"].append("scaffold created .claude config even though Devin target should be .devin")
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
            "pre-tool-use/script.sh",
            "stop/script.sh",
            "session-start/script.sh",
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
        stop_script = generated_root / "stop" / "devin.sh"
        if stop_script.exists():
            stop_payload = json.dumps(
                {
                    "hook_event_name": "Stop",
                    "stop_hook_active": False,
                }
            )
            stop_proc = run(
                ["bash", str(stop_script)],
                cwd=project,
                input_text=stop_payload,
                env={"DEVIN_PROJECT_DIR": str(project)},
            )
            if (
                stop_proc.returncode == 2
                and "portable shared script devin" in stop_proc.stderr
                and "must block" in stop_proc.stderr
                and '"decision": "block"' in stop_proc.stdout
            ):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append(
                    "generated Stop hook did not translate configured failure into exit code 2 with a block decision"
                )
                results["passed"] = False
        else:
            results["errors"].append("generated Stop hook missing before exit-code-2 check")
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
