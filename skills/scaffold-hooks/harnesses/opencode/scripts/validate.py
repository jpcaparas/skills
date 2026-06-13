#!/usr/bin/env python3
"""
validate.py

Validate the opencode harness component of scaffold-hooks harness component structure and its hook-surface manifest.
"""

from __future__ import annotations

import json
import re
import sys
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
REQUIRED_OPERATIONAL_SCRIPTS = [
    "scripts/audit_project.sh",
    "scripts/check_plugin_setup.ts",
    "scripts/merge_opencode_config.ts",
    "scripts/merge_package_json.ts",
    "scripts/opencode_json_utils.ts",
    "scripts/render_plugin_module.ts",
    "scripts/render_hooks_readme.sh",
    "scripts/scaffold_hooks.sh",
    "scripts/validate.py",
    "scripts/test_skill.py",
]
REQUIRED_SUPPORT_FILES = [
    "assets/hook-events.json",
    "templates/hook-plan.example.json",
    "templates/hook-plan.broad.example.json",
    "templates/lifecycle-action-plugin.ts.tmpl",
    "templates/plugin-module.ts.tmpl",
    "references/project-analysis.md",
    "references/config-layering.md",
    "references/hook-events.md",
    "references/plugin-patterns.md",
    "references/scaffold-layout.md",
    "references/reusable-scripts.md",
    "references/merge-strategy.md",
    "references/gotchas.md",
]


def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    if not content.startswith("---"):
        return None, content

    end = content.find("---", 3)
    if end == -1:
        return None, content

    frontmatter_text = content[3:end].strip()
    body = content[end + 3 :].strip()

    frontmatter: dict[str, str] = {}
    for line in frontmatter_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$", line)
        if not match or line.startswith((" ", "\t")):
            continue
        key = match.group(1)
        value = match.group(2).strip()
        if value and value[0] in ('"', "'") and value[-1] == value[0]:
            value = value[1:-1]
        frontmatter[key] = value

    return frontmatter, body


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


def validate_manifest(skill_path: Path, errors: list[str], warnings: list[str]) -> None:
    manifest_path = skill_path / "assets" / "hook-events.json"
    if not manifest_path.is_file():
        errors.append("Missing assets/hook-events.json")
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"assets/hook-events.json is not valid JSON: {exc}")
        return

    events = manifest.get("events", [])
    special_surfaces = manifest.get("special_surfaces", [])
    if not isinstance(events, list):
        errors.append("assets/hook-events.json: 'events' must be an array")
        return
    if not isinstance(special_surfaces, list):
        errors.append("assets/hook-events.json: 'special_surfaces' must be an array")
        return

    event_names = {event.get("name") for event in events}
    special_names = {surface.get("name") for surface in special_surfaces}
    if event_names != EXPECTED_EVENT_NAMES:
        missing = sorted(EXPECTED_EVENT_NAMES - event_names)
        unexpected = sorted(event_names - EXPECTED_EVENT_NAMES)
        if missing:
            errors.append(f"assets/hook-events.json is missing events: {', '.join(missing)}")
        if unexpected:
            errors.append(f"assets/hook-events.json has unexpected events: {', '.join(unexpected)}")
    if special_names != EXPECTED_SPECIAL_SURFACES:
        missing = sorted(EXPECTED_SPECIAL_SURFACES - special_names)
        unexpected = sorted(special_names - EXPECTED_SPECIAL_SURFACES)
        if missing:
            errors.append(
                f"assets/hook-events.json is missing special surfaces: {', '.join(missing)}"
            )
        if unexpected:
            errors.append(
                f"assets/hook-events.json has unexpected special surfaces: {', '.join(unexpected)}"
            )

    stub_files = [item.get("stub_file", "") for item in special_surfaces + events]
    if "" in stub_files:
        errors.append("assets/hook-events.json contains an item without a stub_file")
    if len(set(stub_files)) != len(stub_files):
        errors.append("assets/hook-events.json contains duplicate stub_file values")

    if manifest.get("default_module_format") != "ts":
        errors.append("assets/hook-events.json must default module format to ts")

    non_ts_stubs = [stub for stub in stub_files if not stub.endswith(".ts.txt")]
    if non_ts_stubs:
        errors.append(
            "assets/hook-events.json contains non-TypeScript stub filenames: "
            + ", ".join(sorted(non_ts_stubs))
        )


def validate_skill(skill_path: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    playbook_path = skill_path / "PLAYBOOK.md"
    if not playbook_path.is_file():
        return {"valid": False, "errors": ["PLAYBOOK.md does not exist"], "warnings": warnings, "metrics": metrics}

    content = playbook_path.read_text(encoding="utf-8")
    metrics["skill_md_lines"] = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    metrics["total_lines"] = metrics["skill_md_lines"]

    for ref in extract_file_references(content):
        if not (skill_path / ref).exists():
            errors.append(f"Referenced file does not exist: {ref}")

    required_dirs = ["references", "scripts", "templates", "assets"]
    for dirname in required_dirs:
        if not (skill_path / dirname).is_dir():
            errors.append(f"Missing required directory: {dirname}/")

    for rel_path in REQUIRED_OPERATIONAL_SCRIPTS + REQUIRED_SUPPORT_FILES:
        if not (skill_path / rel_path).exists():
            errors.append(f"Missing required file: {rel_path}")

    if (skill_path / "templates" / "plugin-module.js.tmpl").exists():
        errors.append("Do not ship a JavaScript plugin template; managed plugins must be TypeScript-only")

    lifecycle_template = skill_path / "templates" / "lifecycle-action-plugin.ts.tmpl"
    if lifecycle_template.exists():
        lifecycle_content = lifecycle_template.read_text(encoding="utf-8")
        for snippet in [
            "parentID?: string | null",
            "const childSessionIDs = new Set<string>()",
            "rememberSessionCreation",
            "isChildSession(sessionID)",
            'event.type === "session.deleted"',
        ]:
            if snippet not in lifecycle_content:
                errors.append(f"Lifecycle plugin template missing root-session guard snippet: {snippet}")

    scaffold_script = skill_path / "scripts" / "scaffold_hooks.sh"
    if scaffold_script.exists():
        scaffold_content = scaffold_script.read_text(encoding="utf-8")
        for snippet in [
            "managed_file_hashes",
            "preserved_file_hashes",
            "scaffold_hooks",
            "previous_managed_hash",
            "backup_existing_plugin",
        ]:
            if snippet not in scaffold_content:
                errors.append(f"scaffold_hooks.sh missing incremental provenance snippet: {snippet}")

    validate_manifest(skill_path, errors, warnings)

    refs_dir = skill_path / "references"
    if refs_dir.is_dir():
        for ref_path in refs_dir.rglob("*.md"):
            metrics["reference_count"] += 1
            metrics["total_lines"] += ref_path.read_text(encoding="utf-8").count("\n") + 1

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        return 1

    skill_path = Path(sys.argv[1]).resolve()
    if not skill_path.is_dir():
        print(f"Error: '{skill_path}' is not a directory", file=sys.stderr)
        return 1

    result = validate_skill(skill_path)
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
