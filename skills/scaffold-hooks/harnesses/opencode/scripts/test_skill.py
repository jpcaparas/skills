#!/usr/bin/env python3
"""
test_skill.py

Lightweight checks plus temp-project integration tests for the Froggy-backed
OpenCode harness component of scaffold-hooks.
"""

from __future__ import annotations

import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


EXPECTED_SUPPORTED_EVENTS = {
    "session.created",
    "session.deleted",
    "session.idle",
    "tool.before.*",
    "tool.before.<name>",
    "tool.after.*",
    "tool.after.<name>",
}
BASH_SCRIPTS = [
    "scripts/audit_project.sh",
    "scripts/render_hooks_readme.sh",
    "scripts/scaffold_hooks.sh",
]
TS_SCRIPTS = [
    "scripts/check_plugin_setup.ts",
    "scripts/merge_opencode_config.ts",
    "scripts/opencode_json_utils.ts",
    "scripts/render_froggy_hooks.ts",
]
PYTHON_VALIDATION_SCRIPTS = [
    "scripts/validate.py",
    "scripts/test_skill.py",
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


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(
            cmd,
            127,
            "",
            f"Command not found: {cmd[0]}. Original error: {exc}",
        )


def bun_build_check(entry_path: Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as tmpdir:
        outfile = Path(tmpdir) / "syntax-check.js"
        return run(
            [
                "bun",
                "build",
                "--target=bun",
                "--format=esm",
                "--outfile",
                str(outfile),
                str(entry_path),
            ],
            cwd=cwd,
        )


def missing_runtime_commands() -> list[str]:
    required = ["bash", "bun", "git", "jq"]
    return [command for command in required if shutil.which(command) is None]


def write(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def seed_project(project: Path) -> None:
    project.mkdir()
    run(["git", "init", "-q"], cwd=project)
    write(project / "scripts" / "agent-session-context.sh", "#!/usr/bin/env bash\nexit 0\n", True)
    write(project / "scripts" / "validate-project.sh", "#!/usr/bin/env bash\necho validate\nexit 0\n", True)


def seed_legacy_opencode_scaffold(project: Path) -> None:
    plugin_root = project / ".opencode" / "plugins"
    write(
        plugin_root / ".managed" / "manifest.json",
        json.dumps(
            {
                "deployment": "local-files",
                "mode": "overhaul",
                "module_format": "ts",
                "plugin_root": ".opencode/plugins",
                "managed_files": ["old_lifecycle.ts"],
                "enabled_plugins": [
                    {
                        "name": "old-lifecycle",
                        "pattern": "lifecycle-action",
                        "filename": "old_lifecycle.ts",
                        "context_script": "hooks/opencode-session-created/opencode.sh",
                        "action_script": "hooks/opencode-session-idle/opencode.sh",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
    )
    write(plugin_root / "old_lifecycle.ts", "/* Managed by scaffold-hooks */\nexport default async () => ({})\n")
    write(plugin_root / "README.md", "# OpenCode Hooks\n\nGenerated old README.\n")
    write(project / ".opencode" / "package.json", '{"dependencies":{"@opencode-ai/plugin":"1.15.10"}}\n')
    write(project / ".opencode" / "package-lock.json", "{}\n")
    write(project / ".opencode" / ".gitignore", "node_modules\npackage.json\npackage-lock.json\nbun.lock\n.gitignore\n")
    write(
        project / "hooks" / "opencode-session-created" / "script.sh",
        "#!/usr/bin/env bash\nprintf '[opencode-hook] missing delegate: %s\\n' foo >&2\n",
        True,
    )
    write(
        project / "hooks" / "opencode-session-created" / "opencode.sh",
        "#!/usr/bin/env bash\nexport OPENCODE_HOOK_EVENT=opencode-session-created\n",
        True,
    )
    write(
        project / "hooks" / "opencode-session-idle" / "script.sh",
        "#!/usr/bin/env bash\nprintf '[opencode-hook] missing delegate: %s\\n' foo >&2\n",
        True,
    )
    write(
        project / "hooks" / "opencode-session-idle" / "opencode.sh",
        "#!/usr/bin/env bash\nexport OPENCODE_HOOK_EVENT=opencode-session-idle\n",
        True,
    )


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

    manifest = load_json(skill_path / "assets" / "hook-events.json")
    if set(manifest.get("supported_events", [])) != EXPECTED_SUPPORTED_EVENTS:
        results["errors"].append("Froggy supported event manifest drifted unexpectedly")
        results["passed"] = False
    if manifest.get("plugin_name") != "opencode-froggy":
        results["errors"].append("Manifest must identify opencode-froggy")
        results["passed"] = False

    playbook = (skill_path / "PLAYBOOK.md").read_text(encoding="utf-8")
    for snippet in [
        "opencode-froggy",
        ".opencode/hook/hooks.md",
        "cleanup",
        "Do not update this skill from memory",
    ]:
        if snippet not in playbook:
            results["errors"].append(f"PLAYBOOK.md is missing Froggy guidance: {snippet}")
            results["passed"] = False

    for ref in extract_file_references(playbook):
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

    for rel_path in TS_SCRIPTS:
        results["syntax_checks"]["total"] += 1
        proc = bun_build_check(skill_path / rel_path)
        if proc.returncode == 0:
            results["syntax_checks"]["passed"] += 1
        else:
            output = proc.stderr.strip() or proc.stdout.strip()
            results["errors"].append(f"TypeScript syntax check failed for {rel_path}: {output}")
            results["passed"] = False

    for rel_path in PYTHON_VALIDATION_SCRIPTS:
        results["syntax_checks"]["total"] += 1
        try:
            py_compile.compile(str(skill_path / rel_path), doraise=True)
            results["syntax_checks"]["passed"] += 1
        except py_compile.PyCompileError as exc:
            results["errors"].append(f"Python compile failed for {rel_path}: {exc.msg}")
            results["passed"] = False

    missing_runtime = missing_runtime_commands()
    if missing_runtime:
        results["errors"].append(
            "Missing required runtime command(s) for opencode harness integration tests: "
            + ", ".join(missing_runtime)
        )
        results["passed"] = False
        return results

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        home = tmp / "home"
        home.mkdir()

        project = tmp / "project"
        seed_project(project)

        results["integration_checks"]["total"] += 1
        audit = run(["bash", str(skill_path / "scripts" / "audit_project.sh"), str(project)], cwd=skill_path)
        if audit.returncode == 0:
            audit_data = json.loads(audit.stdout)
            if (
                audit_data["opencode"]["recommended_scope"] == "project"
                and audit_data["opencode"]["recommended_hook_config"] == ".opencode/hook/hooks.md"
            ):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("audit_project.sh did not recommend Froggy project-local hook config")
                results["passed"] = False
        else:
            results["errors"].append(f"audit_project.sh failed: {audit.stderr.strip()}")
            results["passed"] = False

        plan = tmp / "plan.json"
        plan.write_text((skill_path / "templates" / "hook-plan.example.json").read_text(encoding="utf-8"), encoding="utf-8")

        results["integration_checks"]["total"] += 1
        scaffold = run(
            [
                "bash",
                str(skill_path / "scripts" / "scaffold_hooks.sh"),
                "--project",
                str(project),
                "--plan",
                str(plan),
                "--home",
                str(home),
            ],
            cwd=skill_path,
        )
        if scaffold.returncode == 0:
            expected_files = [
                project / "opencode.json",
                project / ".opencode" / "hook" / "hooks.md",
                project / ".opencode" / "hook" / "README.md",
                project / ".opencode" / "hook" / ".managed" / "manifest.json",
                project / ".opencode" / "hook" / ".managed" / "plan.snapshot.json",
            ]
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
        config = load_json(project / "opencode.json")
        hooks_md = (project / ".opencode" / "hook" / "hooks.md").read_text(encoding="utf-8")
        if (
            "opencode-froggy" in config.get("plugin", [])
            and "BEGIN scaffold-hooks managed opencode-froggy" in hooks_md
            and "session.idle" in hooks_md
        ):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("scaffold did not enable opencode-froggy and managed hooks.md")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        forbidden = [
            project / ".opencode" / "plugins" / "opencode_hook_project_session_lifecycle.ts",
            project / ".opencode" / "package.json",
            project / ".opencode" / "package-lock.json",
            project / ".opencode" / "node_modules",
        ]
        if not any(path.exists() for path in forbidden):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("Froggy scaffold created old local-plugin dependency artifacts")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        rerun = run(
            [
                "bash",
                str(skill_path / "scripts" / "scaffold_hooks.sh"),
                "--project",
                str(project),
                "--plan",
                str(plan),
                "--home",
                str(home),
            ],
            cwd=skill_path,
        )
        hooks_after_rerun = (project / ".opencode" / "hook" / "hooks.md").read_text(encoding="utf-8")
        if rerun.returncode == 0 and hooks_after_rerun.count("BEGIN scaffold-hooks managed opencode-froggy") == 1:
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("additive rerun duplicated or failed to refresh the managed Froggy block")
            results["passed"] = False

        legacy_project = tmp / "legacy-project"
        seed_project(legacy_project)
        seed_legacy_opencode_scaffold(legacy_project)
        results["integration_checks"]["total"] += 1
        legacy_scaffold = run(
            [
                "bash",
                str(skill_path / "scripts" / "scaffold_hooks.sh"),
                "--project",
                str(legacy_project),
                "--plan",
                str(plan),
                "--home",
                str(home),
            ],
            cwd=skill_path,
        )
        if (
            legacy_scaffold.returncode == 0
            and not (legacy_project / ".opencode" / "plugins" / "old_lifecycle.ts").exists()
            and not (legacy_project / ".opencode" / "plugins" / ".managed").exists()
            and not (legacy_project / ".opencode" / "package.json").exists()
            and not (legacy_project / "hooks" / "opencode-session-idle" / "opencode.sh").exists()
            and (legacy_project / ".opencode" / "hook" / "hooks.md").exists()
        ):
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append(
                "legacy plugin scaffold was not razed during Froggy migration: "
                + (legacy_scaffold.stderr.strip() or legacy_scaffold.stdout.strip())
            )
            results["passed"] = False

        custom_project = tmp / "custom-project"
        seed_project(custom_project)
        write(
            custom_project / ".opencode" / "hook" / "hooks.md",
            "---\nhooks:\n  - event: tool.after.write\n    actions:\n      - bash: \"echo custom\"\n---\n# Custom hooks\n",
        )
        results["integration_checks"]["total"] += 1
        custom_scaffold = run(
            [
                "bash",
                str(skill_path / "scripts" / "scaffold_hooks.sh"),
                "--project",
                str(custom_project),
                "--plan",
                str(plan),
                "--home",
                str(home),
            ],
            cwd=skill_path,
        )
        custom_hooks = (custom_project / ".opencode" / "hook" / "hooks.md").read_text(encoding="utf-8")
        if custom_scaffold.returncode == 0 and "echo custom" in custom_hooks and "session.idle" in custom_hooks:
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("scaffold did not preserve appendable custom Froggy hooks")
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
