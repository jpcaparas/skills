#!/usr/bin/env python3
"""Check scaffold output and migration boundaries in disposable projects."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
OUTPUTS = {
    "claude": {"managed_root": "hooks", "settings_target": ".claude/settings.json"},
    "codex": {"managed_root": "hooks", "hooks_target": ".codex/hooks.json"},
    "copilot": {
        "managed_root": ".github/copilot/hooks/generated",
        "hooks_target": ".github/hooks/copilot-hooks.json",
    },
    "devin": {"managed_root": "hooks", "hooks_target": ".devin/hooks.v1.json"},
    "opencode": {
        "hooks_root": "hooks",
        "config_target": "opencode.json",
        "hook_config_target": ".opencode/hook/hooks.md",
        "managed_state_dir": ".opencode/hook/.managed",
    },
}
MERGERS = {
    "claude": ("merge_settings.sh", "--settings-file"),
    "codex": ("merge_hooks_json.sh", "--hooks-file"),
    "copilot": ("merge_hooks_file.sh", "--hooks-file"),
    "devin": ("merge_hooks_file.sh", "--hooks-file"),
}


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def snapshot(root: Path) -> dict[str, tuple[int, bytes | str | None]]:
    """Include link identity and modes, not just outside-file contents."""
    result: dict[str, tuple[int, bytes | str | None]] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if relative.parts[0] == ".git":
            continue
        content: bytes | str | None = None
        if path.is_symlink():
            content = os.readlink(path)
        elif path.is_file():
            content = path.read_bytes()
        result[str(relative)] = (path.lstat().st_mode, content)
    return result


class ScaffoldSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        # Successful scaffolders execute bundled scripts; do not depend on /tmp
        # being executable on the host running the package suite.
        temporary = tempfile.TemporaryDirectory(prefix=".security-test-", dir=SKILL)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.outside = self.root / "outside"
        self.outside.mkdir()
        self.home = self.root / "home"
        self.home.mkdir()
        self.sentinel = self.outside / "private.json"
        write(self.sentinel, '{"private": "must not enter project config"}\n')
        self.sentinel.chmod(0o600)
        self.plan_path = self.root / "plan.json"
        self.project = self.new_project()

    def new_project(self) -> Path:
        project = Path(tempfile.mkdtemp(prefix="project-", dir=self.root))
        result = self.run_command(["git", "init", "-q", str(project)])
        self.assertEqual(0, result.returncode, result.stderr)
        return project

    def run_command(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            command, cwd=SKILL, capture_output=True, text=True, timeout=45,
            env={**os.environ, "HOME": str(self.home)},
        )

    def plan(self, harness: str) -> dict[str, object]:
        directory = SKILL if harness == "universal" else SKILL / "harnesses" / harness
        data: dict[str, object] = json.loads(
            (directory / "templates/hook-plan.example.json").read_text(encoding="utf-8")
        )
        return data

    def scaffold_command(
        self, harness: str, plan: dict[str, object], *options: str,
    ) -> list[str]:
        write(self.plan_path, json.dumps(plan))
        script = (
            SKILL / "scripts/scaffold_all_hooks.sh" if harness == "universal"
            else SKILL / "harnesses" / harness / "scripts/scaffold_hooks.sh"
        )
        return [
            "bash", str(script), "--project", str(self.project),
            "--plan", str(self.plan_path), *options,
        ]

    def assert_rejected(self, command: list[str], diagnostic: str = "Unsafe scaffold path") -> None:
        before = [snapshot(root) for root in (self.project, self.outside, self.home)]
        result = self.run_command(command)
        self.assertNotEqual(0, result.returncode, result.stdout)
        self.assertIn(diagnostic, result.stderr)
        self.assertEqual(before, [snapshot(root) for root in (self.project, self.outside, self.home)])

    def test_project_outputs_reject_escaping_paths_before_writes(self) -> None:
        for harness, fields in OUTPUTS.items():
            for field in fields:
                for target in ("../outside/private.json", str(self.sentinel), "~/private.json"):
                    with self.subTest(harness=harness, field=field, target=target):
                        plan = self.plan(harness)
                        plan[field] = target
                        self.assert_rejected(self.scaffold_command(harness, plan))

    def test_symlinked_outputs_and_parents_are_rejected(self) -> None:
        for harness, fields in OUTPUTS.items():
            for field, relative in fields.items():
                for at_parent in (False, True):
                    # opencode.json is at the selected root, which is not an output.
                    if at_parent and len(Path(relative).parts) == 1:
                        continue
                    with self.subTest(harness=harness, field=field, at_parent=at_parent):
                        self.project = self.new_project()
                        link = self.project / (Path(relative).parent if at_parent else relative)
                        link.parent.mkdir(parents=True, exist_ok=True)
                        is_directory = at_parent or field in {"managed_root", "managed_state_dir", "hooks_root"}
                        target = self.outside if is_directory else self.sentinel
                        link.symlink_to(target, target_is_directory=is_directory)
                        self.assert_rejected(self.scaffold_command(harness, self.plan(harness)))

    def test_descendant_symlinks_cannot_redirect_generated_writes_or_chmod(self) -> None:
        leaves = {
            "claude": "hooks/lib/claude.sh",
            "codex": "hooks/lib/codex.sh",
            "devin": "hooks/lib/devin.sh",
            "copilot": ".github/copilot/hooks/generated/lib/common.sh",
            "opencode": ".opencode/hook/.managed/plan.snapshot.json",
        }
        for harness, relative in leaves.items():
            for mode in ("additive", "overhaul"):
                with self.subTest(harness=harness, mode=mode):
                    self.project = self.new_project()
                    link = self.project / relative
                    link.parent.mkdir(parents=True)
                    link.symlink_to(self.sentinel)
                    self.assert_rejected(self.scaffold_command(harness, self.plan(harness), "--mode", mode))

    def test_dangling_config_link_is_not_replaced_or_populated(self) -> None:
        for harness, fields in OUTPUTS.items():
            with self.subTest(harness=harness):
                self.project = self.new_project()
                config = next(path for field, path in fields.items() if field.endswith("target"))
                link = self.project / config
                link.parent.mkdir(parents=True, exist_ok=True)
                link.symlink_to(self.outside / "not-created.json")
                self.assert_rejected(self.scaffold_command(harness, self.plan(harness)))

    def test_standalone_mergers_do_not_copy_private_symlink_targets(self) -> None:
        fragment = self.root / "fragment.json"
        # Use valid hook configuration so rejection cannot come from a parser
        # error after the private target has already been read.
        write(self.sentinel, json.dumps({
            "Stop": [{"hooks": [{"type": "command", "command": "printf private-marker"}]}],
        }))
        for harness, (script, flag) in MERGERS.items():
            with self.subTest(harness=harness):
                write(fragment, "{}\n" if harness == "devin" else '{"hooks": {}}\n')
                self.project = self.new_project()
                config = self.project / "config.json"
                config.symlink_to(self.sentinel)
                self.assert_rejected([
                    "bash", str(SKILL / "harnesses" / harness / "scripts" / script),
                    flag, str(config), "--fragment-file", str(fragment), "--managed-root", "hooks",
                ])

    def test_codex_feature_config_symlink_is_rejected_before_scaffolding(self) -> None:
        for scope in ("project", "user"):
            with self.subTest(scope=scope):
                self.project = self.new_project()
                config = (self.project if scope == "project" else self.home) / ".codex/config.toml"
                config.parent.mkdir(parents=True, exist_ok=True)
                config.symlink_to(self.sentinel)
                self.assert_rejected(self.scaffold_command(
                    "codex", self.plan("codex"), "--ensure-feature", scope,
                ))

    def test_universal_preflights_later_harness_before_overhaul_or_config_changes(self) -> None:
        for target in ("../outside/private.json", str(self.sentinel)):
            with self.subTest(target=target):
                self.project = self.new_project()
                write(self.project / "hooks/stop/claude.sh", "original adapter\n")
                write(self.project / ".claude/settings.json", '{"hooks": {}}\n')
                plan = self.plan("universal")
                plan["harnesses"] = ["claude", "opencode"]
                plan["plans"] = {
                    "claude": self.plan("claude"),
                    "opencode": {**self.plan("opencode"), "config_target": target},
                }
                self.assert_rejected(self.scaffold_command("universal", plan, "--mode", "overhaul"))

    def test_universal_rejects_unsafe_shared_root_and_legacy_cleanup_symlinks(self) -> None:
        plan = self.plan("universal")
        plan["harnesses"] = ["claude"]
        self.assert_rejected(self.scaffold_command(
            "universal", {**plan, "hooks_root": "../outside"}, "--mode", "overhaul",
        ))
        for relative in ("hooks/.state", ".codex/hooks/generated"):
            with self.subTest(relative=relative):
                self.project = self.new_project()
                link = self.project / relative
                link.parent.mkdir(parents=True)
                link.symlink_to(self.outside, target_is_directory=True)
                self.assert_rejected(self.scaffold_command("universal", plan, "--mode", "overhaul"))

    def test_opencode_legacy_manifest_cannot_delete_outside_files(self) -> None:
        for root, files in (
            ("../outside", ["private.json"]),
            (str(self.outside), ["private.json"]),
            (".opencode/plugins", ["../../../outside/private.json"]),
            (".opencode/plugins", [str(self.sentinel)]),
        ):
            with self.subTest(root=root, files=files):
                self.project = self.new_project()
                write(self.project / ".opencode/plugins/.managed/manifest.json", json.dumps({
                    "scaffold_hooks": {"skill_name": "scaffold-hooks", "harness": "opencode"},
                    "plugin_root": root,
                    "managed_files": files,
                }))
                self.assert_rejected(self.scaffold_command("opencode", self.plan("opencode")))

    def test_global_opencode_requires_authorization_and_stays_in_config_root(self) -> None:
        plan = self.plan("opencode")
        for field in ("config_target", "hook_config_target", "managed_state_dir"):
            del plan[field]
        plan["scope"] = "global"
        self.assert_rejected(
            self.scaffold_command("opencode", plan), "requires explicit --allow-global-targets",
        )
        for target in ("~/.ssh/config", "~/.config/opencode/../../../outside/private.json"):
            with self.subTest(target=target):
                self.assert_rejected(self.scaffold_command(
                    "opencode", {**plan, "config_target": target}, "--allow-global-targets",
                ))
        result = self.run_command(self.scaffold_command("opencode", plan, "--allow-global-targets"))
        self.assertEqual(0, result.returncode, result.stderr)
        config = self.home / ".config/opencode/opencode.json"
        self.assertEqual(["opencode-froggy"], json.loads(config.read_text(encoding="utf-8"))["plugin"])
        self.assertIn("session.idle", (config.parent / "hook/hooks.md").read_text(encoding="utf-8"))
        self.assertFalse((self.project / "opencode.json").exists())

        universal = self.plan("universal")
        universal.update({"harnesses": ["opencode"], "plans": {"opencode": plan}})
        self.assert_rejected(
            self.scaffold_command("universal", universal), "requires explicit --allow-global-targets",
        )
        result = self.run_command(self.scaffold_command("universal", universal, "--allow-global-targets"))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(["opencode-froggy"], json.loads(config.read_text(encoding="utf-8"))["plugin"])
        self.assertFalse((self.project / "opencode.json").exists())

    def test_valid_nested_root_and_unselected_config_are_preserved(self) -> None:
        unrelated = self.project / ".codex/hooks.json"
        unrelated.parent.mkdir()
        unrelated.symlink_to(self.sentinel)
        plan = self.plan("universal")
        plan.update({"harnesses": ["claude"], "hooks_root": "nested/hooks..safe", "cleanup_legacy": False})
        outside_before = snapshot(self.outside)
        result = self.run_command(self.scaffold_command("universal", plan))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((self.project / "nested/hooks..safe/stop/claude.sh").is_file())
        self.assertTrue(unrelated.is_symlink())
        self.assertEqual(outside_before, snapshot(self.outside))

    def test_refresh_keeps_pinned_opencode_plugin_without_bare_duplicate(self) -> None:
        config = self.project / "opencode.json"
        plugins = ["opencode-froggy-extra", "opencode-froggy@0.12.0", "@example/other@1.2.3"]
        write(config, json.dumps({"plugin": plugins, "model": "provider/model"}))
        for _ in range(2):
            result = self.run_command(self.scaffold_command("opencode", self.plan("opencode")))
            self.assertEqual(0, result.returncode, result.stderr)
            data = json.loads(config.read_text(encoding="utf-8"))
            self.assertEqual(plugins, data["plugin"])
            self.assertEqual("provider/model", data["model"])
        result = self.run_command([
            "bun", str(SKILL / "harnesses/opencode/scripts/check_plugin_setup.ts"),
            "--project", str(self.project), "--json",
        ])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)["project"]["has_froggy_plugin"])


if __name__ == "__main__":
    unittest.main()
