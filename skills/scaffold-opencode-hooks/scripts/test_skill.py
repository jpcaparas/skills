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
import shutil
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
TS_SCRIPTS = [
    "scripts/check_plugin_setup.ts",
    "scripts/merge_opencode_config.ts",
    "scripts/merge_package_json.ts",
    "scripts/opencode_json_utils.ts",
    "scripts/render_plugin_module.ts",
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


def bun_import_check(entry_path: Path, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return run(
        [
            "bun",
            "--no-install",
            "--eval",
            f"await import({json.dumps(entry_path.as_uri())})",
        ],
        cwd=cwd,
    )


def missing_runtime_commands() -> list[str]:
    required = ["bash", "bun", "git", "jq"]
    return [command for command in required if shutil.which(command) is None]


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
    for snippet in [
        "## Progressive Maintainer Drift Check",
        "Live-fetch the official OpenCode plugin",
        "npm view @opencode-ai/plugin version",
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
            "Missing required runtime command(s) for scaffold-opencode-hooks integration tests: "
            + ", ".join(missing_runtime)
            + ". Install Bun, jq, git, and bash before running this test. "
            + "GitHub Actions uses oven-sh/setup-bun for TypeScript execution."
        )
        results["passed"] = False
        return results

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
                "bun",
                str(skill_path / "scripts" / "check_plugin_setup.ts"),
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
            if (
                data["scope_recommendation"] == "project"
                and data["recommended_module_format"] == "ts"
                and not data["project"]["local_plugin_files"]
            ):
                results["integration_checks"]["passed"] += 1
            else:
                results["errors"].append("check_plugin_setup.ts returned unexpected initial state")
                results["passed"] = False
        else:
            results["errors"].append(f"check_plugin_setup.ts failed before scaffold: {inspect_before.stderr.strip()}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        config_jsonc = project / "opencode.jsonc"
        config_jsonc.write_text(
            '{\n  // existing plugin config\n  "plugin": ["existing-plugin"]\n}\n',
            encoding="utf-8",
        )
        merge_config = run(
            [
                "bun",
                str(skill_path / "scripts" / "merge_opencode_config.ts"),
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
                results["errors"].append("merge_opencode_config.ts did not merge plugin entries correctly")
                results["passed"] = False
        else:
            results["errors"].append(f"merge_opencode_config.ts failed: {merge_config.stderr.strip()}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        package_target = project / ".opencode" / "package.json"
        merge_package = run(
            [
                "bun",
                str(skill_path / "scripts" / "merge_package_json.ts"),
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
                results["errors"].append("merge_package_json.ts did not create module package.json correctly")
                results["passed"] = False
        else:
            results["errors"].append(f"merge_package_json.ts failed: {merge_package.stderr.strip()}")
            results["passed"] = False

        minimal_project = tmp / "minimal-project"
        minimal_project.mkdir()
        (minimal_project / "package.json").write_text(
            json.dumps({"name": "minimal-project", "scripts": {"validate": "bash scripts/validate-project.sh"}}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        (minimal_project / "scripts").mkdir()
        (minimal_project / "scripts" / "agent-session-context.sh").write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "printf '## Project Session Context\\nUse repo-owned scripts for validation.\\n'\n",
            encoding="utf-8",
        )
        (minimal_project / "scripts" / "validate-project.sh").write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [ -f .pass-validation ]; then\n"
            "  printf 'validation passed\\n'\n"
            "  exit 0\n"
            "fi\n"
            "printf 'validation failed\\n' >&2\n"
            "exit 1\n",
            encoding="utf-8",
        )
        run(["git", "init"], cwd=minimal_project)

        temp_plan = tmp / "minimal-plan.json"
        plan_data = load_json(skill_path / "templates" / "hook-plan.example.json")
        temp_plan.write_text(json.dumps(plan_data, indent=2) + "\n", encoding="utf-8")

        results["integration_checks"]["total"] += 1
        scaffold = run(
            [
                "bash",
                str(skill_path / "scripts" / "scaffold_hooks.sh"),
                "--project",
                str(minimal_project),
                "--plan",
                str(temp_plan),
                "--home",
                str(home),
            ],
            cwd=skill_path,
        )
        if scaffold.returncode == 0:
            expected_files = [
                minimal_project / ".opencode" / "plugins" / "README.md",
                minimal_project / ".opencode" / "plugins" / ".managed" / "manifest.json",
                minimal_project / ".opencode" / "plugins" / ".managed" / "plan.snapshot.json",
                minimal_project / ".opencode" / "plugins" / "opencode_hook_project_session_lifecycle.ts",
            ]
            if all(path.exists() for path in expected_files):
                results["integration_checks"]["passed"] += 1
            else:
                missing = [str(path.relative_to(minimal_project)) for path in expected_files if not path.exists()]
                results["errors"].append(f"scaffold_hooks.sh missed files: {', '.join(missing)}")
                results["passed"] = False
        else:
            results["errors"].append(f"scaffold_hooks.sh failed: {scaffold.stderr.strip()}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        generated_js = sorted(
            path.relative_to(minimal_project).as_posix()
            for path in (minimal_project / ".opencode" / "plugins").rglob("*.js")
        ) if (minimal_project / ".opencode" / "plugins").is_dir() else []
        if not generated_js:
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append(f"scaffold generated JavaScript files: {', '.join(generated_js)}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        dependency_churn = [
            rel_path
            for rel_path in [
                ".opencode/package.json",
                ".opencode/node_modules",
                ".opencode/package-lock.json",
                ".opencode/bun.lock",
                ".opencode/bun.lockb",
            ]
            if (minimal_project / rel_path).exists()
        ]
        if not dependency_churn:
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append(
                "minimal scaffold created config-dir dependency artifacts: "
                + ", ".join(dependency_churn)
            )
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        surfaces_dir = minimal_project / ".opencode" / "plugins" / ".managed" / "surfaces"
        if not surfaces_dir.exists():
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append("minimal scaffold unexpectedly created a broad surface catalog")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        plugin_file = minimal_project / ".opencode" / "plugins" / "opencode_hook_project_session_lifecycle.ts"
        proc = bun_import_check(plugin_file, cwd=minimal_project)
        if proc.returncode == 0:
            results["integration_checks"]["passed"] += 1
        else:
            output = proc.stderr.strip() or proc.stdout.strip()
            results["errors"].append(f"generated lifecycle plugin syntax check failed: {output}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        simulator = tmp / "simulate-lifecycle-plugin.mjs"
        simulator.write_text(
            f"""
import {{ writeFileSync }} from "node:fs"
import pluginFactory from {json.dumps(plugin_file.as_uri())}

const toasts = []
const prompts = []
const logs = []
const client = {{
  tui: {{ showToast: async (input) => toasts.push(input.body) }},
  app: {{ log: async (input) => logs.push(input.body) }},
  session: {{ prompt: async (input) => prompts.push(input.body) }},
}}

const plugin = await pluginFactory({{ client, directory: {json.dumps(minimal_project.as_posix())} }})
await plugin.event({{ event: {{ type: "session.created", properties: {{ info: {{ id: "s1" }} }} }} }})
await plugin.event({{ event: {{ type: "session.idle", properties: {{ sessionID: "s1" }} }} }})
await plugin.event({{ event: {{ type: "session.idle", properties: {{ sessionID: "s1" }} }} }})
await plugin.event({{ event: {{ type: "session.idle", properties: {{ sessionID: "s1" }} }} }})
writeFileSync({json.dumps((minimal_project / ".pass-validation").as_posix())}, "ok\\n", "utf8")
await plugin.event({{ event: {{ type: "session.idle", properties: {{ sessionID: "s1" }} }} }})

const variants = toasts.map((toast) => toast.variant)
const messages = toasts.map((toast) => toast.message)
if (!variants.includes("info")) throw new Error("missing info toast")
if (!variants.includes("success")) throw new Error("missing success toast")
if (!variants.includes("error")) throw new Error("missing error toast")
if (!messages.some((message) => message.includes("Project validation started"))) throw new Error("missing start toast")
if (!messages.some((message) => message.includes("Project validation passed"))) throw new Error("missing pass toast")
if (!messages.some((message) => message.includes("Project validation failed"))) throw new Error("missing fail toast")
if (!messages.some((message) => message.includes("still failing"))) throw new Error("missing persistent failure toast")
if (prompts.length !== 3) throw new Error(`expected 3 prompts, got ${{prompts.length}}`)
if (prompts[0].noReply !== true) throw new Error("session context prompt must be noReply")
if (prompts[1].noReply === true) throw new Error("first repair prompt must allow a reply")
if (prompts[2].noReply !== true) throw new Error("persistent failure prompt must be noReply")
if (logs.length === 0) throw new Error("expected diagnostic app logs")
""".lstrip(),
            encoding="utf-8",
        )
        simulation = run(["bun", "--no-install", str(simulator)], cwd=minimal_project)
        if simulation.returncode == 0:
            results["integration_checks"]["passed"] += 1
        else:
            results["errors"].append(
                "generated lifecycle plugin did not satisfy toast/repair simulation: "
                + (simulation.stderr.strip() or simulation.stdout.strip())
            )
            results["passed"] = False

        broad_project = tmp / "broad-project"
        broad_project.mkdir()
        (broad_project / "package.json").write_text(
            json.dumps({"name": "broad-project"}, indent=2) + "\n",
            encoding="utf-8",
        )
        run(["git", "init"], cwd=broad_project)
        broad_plan = tmp / "broad-plan.json"
        broad_plan.write_text(
            (skill_path / "templates" / "hook-plan.broad.example.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        results["integration_checks"]["total"] += 1
        broad_scaffold = run(
            [
                "bash",
                str(skill_path / "scripts" / "scaffold_hooks.sh"),
                "--project",
                str(broad_project),
                "--plan",
                str(broad_plan),
                "--home",
                str(home),
            ],
            cwd=skill_path,
        )
        if broad_scaffold.returncode == 0:
            broad_expected = [
                broad_project / ".opencode" / "plugins" / "opencode_hook_guard_sensitive_files.ts",
                broad_project / ".opencode" / "plugins" / "opencode_hook_post_turn_check.ts",
                broad_project / ".opencode" / "plugins" / "opencode_hook_shell_env.ts",
                broad_project / ".opencode" / "plugins" / ".managed" / "surfaces",
            ]
            if all(path.exists() for path in broad_expected):
                results["integration_checks"]["passed"] += 1
            else:
                missing = [str(path.relative_to(broad_project)) for path in broad_expected if not path.exists()]
                results["errors"].append(f"broad scaffold missed files: {', '.join(missing)}")
                results["passed"] = False
        else:
            results["errors"].append(f"broad scaffold failed: {broad_scaffold.stderr.strip()}")
            results["passed"] = False

        results["integration_checks"]["total"] += 1
        manifest_path = broad_project / ".opencode" / "plugins" / ".managed" / "manifest.json"
        if manifest_path.exists():
            manifest_data = load_json(manifest_path)
            stub_dir = broad_project / ".opencode" / "plugins" / ".managed" / "surfaces"
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
            broad_project / ".opencode" / "plugins" / "opencode_hook_guard_sensitive_files.ts",
            broad_project / ".opencode" / "plugins" / "opencode_hook_post_turn_check.ts",
            broad_project / ".opencode" / "plugins" / "opencode_hook_shell_env.ts",
        ]
        parse_errors: list[str] = []
        for plugin_file in plugin_files:
            proc = bun_import_check(plugin_file, cwd=broad_project)
            if proc.returncode != 0:
                output = proc.stderr.strip() or proc.stdout.strip()
                parse_errors.append(f"{plugin_file.name}: {output}")
        if parse_errors:
            results["errors"].extend(parse_errors)
            results["passed"] = False
        else:
            results["integration_checks"]["passed"] += 1

        results["integration_checks"]["total"] += 1
        custom_plugin = minimal_project / ".opencode" / "plugins" / "custom_local_plugin.ts"
        custom_plugin.write_text("const plugin = async () => ({})\nexport default plugin\n", encoding="utf-8")
        config_path = minimal_project / "opencode.json"
        config_path.write_text(json.dumps({"plugin": ["custom-third-party"]}, indent=2) + "\n", encoding="utf-8")
        rerun = run(
            [
                "bash",
                str(skill_path / "scripts" / "scaffold_hooks.sh"),
                "--project",
                str(minimal_project),
                "--plan",
                str(temp_plan),
                "--home",
                str(home),
            ],
            cwd=skill_path,
        )
        if rerun.returncode == 0:
            config_after = json.loads(config_path.read_text(encoding="utf-8"))
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
