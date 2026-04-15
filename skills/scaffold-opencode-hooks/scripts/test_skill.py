#!/usr/bin/env python3
"""
test_skill.py

Lightweight checks plus temp-project integration tests for scaffold-opencode-hooks.
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


EXPECTED_SPECIAL_SURFACES = {"event", "tool"}
EXPECTED_EVENT_NAMES = {
    "command.executed",
    "file.edited",
    "file.watcher.updated",
    "installation.updated",
    "lsp.client.diagnostics",
    "lsp.updated",
    "message.part.removed",
    "message.part.updated",
    "message.removed",
    "message.updated",
    "permission.asked",
    "permission.replied",
    "server.connected",
    "session.created",
    "session.compacted",
    "session.deleted",
    "session.diff",
    "session.error",
    "session.idle",
    "session.status",
    "session.updated",
    "todo.updated",
    "shell.env",
    "tool.execute.after",
    "tool.execute.before",
    "tui.prompt.append",
    "tui.command.execute",
    "tui.toast.show",
    "experimental.session.compacting",
}
BASH_SCRIPTS = [
    "scripts/audit_project.sh",
    "scripts/render_hooks_readme.sh",
    "scripts/scaffold_hooks.sh",
]
PYTHON_SCRIPTS = [
    "scripts/check_plugin_setup.py",
    "scripts/merge_opencode_config.py",
    "scripts/merge_package_json.py",
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
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        check=False,
        capture_output=True,
        text=True,
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
    special_names = {item.get("name") for item in manifest.get("special_surfaces", [])}
    if manifest_names != EXPECTED_EVENT_NAMES:
        missing = sorted(EXPECTED_EVENT_NAMES - manifest_names)
        unexpected = sorted(manifest_names - EXPECTED_EVENT_NAMES)
        if missing:
            results["errors"].append(f"Manifest is missing events: {', '.join(missing)}")
        if unexpected:
            results["errors"].append(f"Manifest contains unexpected events: {', '.join(unexpected)}")
        results["passed"] = False
    if special_names != EXPECTED_SPECIAL_SURFACES:
        missing = sorted(EXPECTED_SPECIAL_SURFACES - special_names)
        unexpected = sorted(special_names - EXPECTED_SPECIAL_SURFACES)
        if missing:
            results["errors"].append(f"Manifest is missing special surfaces: {', '.join(missing)}")
        if unexpected:
            results["errors"].append(
                f"Manifest contains unexpected special surfaces: {', '.join(unexpected)}"
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

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        home = tmp / "home"
        project = tmp / "project"
        home.mkdir()
        project.mkdir()
        (project / ".opencode").mkdir()
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
        run(["git", "init"], cwd=project)

        results["integration_checks"]["total"] += 1
        audit = run(["bash", str(skill_path / "scripts" / "audit_project.sh"), str(project)], cwd=skill_path)
        if audit.returncode == 0:
            audit_data = json.loads(audit.stdout)
            if (
                audit_data["opencode"]["recommended_scope"] == "project"
                and audit_data["opencode"]["recommended_plugin_root"] == ".opencode/plugins"
            ):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("audit_project.sh did not recommend project-local OpenCode scaffold")
                results["passed"] = False
        else:
            results["errors"].append(f"audit_project.sh failed: {audit.stderr.strip()}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        inspect_before = run(
            [
                "python3",
                str(skill_path / "scripts" / "check_plugin_setup.py"),
                "--project",
                str(project),
                "--home",
                str(home),
                "--json",
            ],
            cwd=skill_path,
        )
        if inspect_before.returncode == 0:
            data = json.loads(inspect_before.stdout)
            if data["scope_recommendation"] == "project" and not data["project"]["local_plugin_files"]:
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("check_plugin_setup.py returned unexpected initial state")
                results["passed"] = False
        else:
            results["errors"].append(f"check_plugin_setup.py failed before scaffold: {inspect_before.stderr.strip()}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        config_jsonc = project / "opencode.jsonc"
        config_jsonc.write_text(
            '{\n  // existing plugin config\n  "plugin": ["existing-plugin"]\n}\n',
            encoding="utf-8",
        )
        merge_config = run(
            [
                "python3",
                str(skill_path / "scripts" / "merge_opencode_config.py"),
                "--config-file",
                str(config_jsonc),
                "--plugins",
                "existing-plugin",
                "opencode-wakatime",
            ],
            cwd=skill_path,
        )
        if merge_config.returncode == 0:
            merged = json.loads(config_jsonc.read_text(encoding="utf-8"))
            if merged.get("plugin") == ["existing-plugin", "opencode-wakatime"]:
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("merge_opencode_config.py did not merge plugin entries correctly")
                results["passed"] = False
        else:
            results["errors"].append(f"merge_opencode_config.py failed: {merge_config.stderr.strip()}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        package_target = project / ".opencode" / "package.json"
        merge_package = run(
            [
                "python3",
                str(skill_path / "scripts" / "merge_package_json.py"),
                "--package-file",
                str(package_target),
                "--dependencies-json",
                '{"zod":"^3.25.0"}',
            ],
            cwd=skill_path,
        )
        if merge_package.returncode == 0:
            package_data = json.loads(package_target.read_text(encoding="utf-8"))
            if package_data.get("type") == "module" and package_data.get("dependencies", {}).get("zod") == "^3.25.0":
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("merge_package_json.py did not create module package.json correctly")
                results["passed"] = False
        else:
            results["errors"].append(f"merge_package_json.py failed: {merge_package.stderr.strip()}")
            results["passed"] = False

        temp_plan = tmp / "plan.json"
        plan_data = load_json(skill_path / "templates" / "hook-plan.example.json")
        plan_data["npm_plugins"] = ["opencode-wakatime"]
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
                "--home",
                str(home),
            ],
            cwd=skill_path,
        )
        if scaffold.returncode == 0:
            expected_files = [
                project / "opencode.json",
                project / ".opencode" / "package.json",
                project / ".opencode" / "plugins" / "README.md",
                project / ".opencode" / "plugins" / ".managed" / "manifest.json",
                project / ".opencode" / "plugins" / ".managed" / "plan.snapshot.json",
            ]
            expected_files.extend(
                project / ".opencode" / "plugins" / filename
                for filename in [
                    "opencode_hook_guard_sensitive_files.js",
                    "opencode_hook_post_turn_check.js",
                    "opencode_hook_shell_env.js",
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
        manifest_path = project / ".opencode" / "plugins" / ".managed" / "manifest.json"
        if manifest_path.exists():
            manifest_data = load_json(manifest_path)
            stub_dir = project / ".opencode" / "plugins" / ".managed" / "surfaces"
            expected_stub_count = len(manifest_data["special_surfaces"]) + len(manifest_data["events"])
            actual_stub_count = len(list(stub_dir.glob("*.txt")))
            if expected_stub_count == actual_stub_count:
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("Managed surface stub count did not match manifest")
                results["passed"] = False
        else:
            results["errors"].append("manifest.json was not created before stub-count check")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        plugin_files = [
            project / ".opencode" / "plugins" / "opencode_hook_guard_sensitive_files.js",
            project / ".opencode" / "plugins" / "opencode_hook_post_turn_check.js",
            project / ".opencode" / "plugins" / "opencode_hook_shell_env.js",
        ]
        parse_errors: list[str] = []
        for plugin_file in plugin_files:
            proc = run(["node", "--check", str(plugin_file)], cwd=project)
            if proc.returncode != 0:
                parse_errors.append(f"{plugin_file.name}: {proc.stderr.strip()}")
        if parse_errors:
            results["errors"].extend(parse_errors)
            results["passed"] = False
        else:
            results["integration_checks"]["passed"] += 1

        results["integration_checks"]["total"] += 1
        custom_plugin = project / ".opencode" / "plugins" / "custom_local_plugin.js"
        custom_plugin.write_text("export default async () => ({})\n", encoding="utf-8")
        config_data = json.loads((project / "opencode.json").read_text(encoding="utf-8"))
        config_data.setdefault("plugin", []).append("custom-third-party")
        (project / "opencode.json").write_text(json.dumps(config_data, indent=2) + "\n", encoding="utf-8")
        rerun = run(
            [
                "bash",
                str(skill_path / "scripts" / "scaffold_hooks.sh"),
                "--project",
                str(project),
                "--plan",
                str(temp_plan),
                "--home",
                str(home),
            ],
            cwd=skill_path,
        )
        if rerun.returncode == 0:
            config_after = json.loads((project / "opencode.json").read_text(encoding="utf-8"))
            if custom_plugin.exists() and "custom-third-party" in config_after.get("plugin", []):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("additive scaffold removed a custom plugin file or config entry")
                results["passed"] = False
        else:
            results["errors"].append(f"second scaffold run failed: {rerun.stderr.strip()}")
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

