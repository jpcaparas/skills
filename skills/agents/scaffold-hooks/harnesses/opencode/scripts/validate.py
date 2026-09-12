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


EXPECTED_SUPPORTED_EVENTS = {
    "session.created",
    "session.deleted",
    "session.idle",
    "tool.before.*",
    "tool.before.<name>",
    "tool.after.*",
    "tool.after.<name>",
}
REQUIRED_OPERATIONAL_SCRIPTS = [
    "scripts/audit_project.sh",
    "scripts/check_plugin_setup.ts",
    "scripts/merge_opencode_config.ts",
    "scripts/opencode_json_utils.ts",
    "scripts/render_froggy_hooks.ts",
    "scripts/render_hooks_readme.sh",
    "scripts/scaffold_hooks.sh",
    "scripts/validate.py",
    "scripts/test_skill.py",
]
REQUIRED_SUPPORT_FILES = [
    "assets/hook-events.json",
    "templates/hook-plan.example.json",
    "templates/hook-plan.broad.example.json",
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

    supported_events = manifest.get("supported_events", [])
    conditions = manifest.get("conditions", [])
    actions = manifest.get("actions", [])
    if not isinstance(supported_events, list):
        errors.append("assets/hook-events.json: 'supported_events' must be an array")
        return
    event_names = set(supported_events)
    if event_names != EXPECTED_SUPPORTED_EVENTS:
        missing = sorted(EXPECTED_SUPPORTED_EVENTS - event_names)
        unexpected = sorted(event_names - EXPECTED_SUPPORTED_EVENTS)
        if missing:
            errors.append(f"assets/hook-events.json is missing supported events: {', '.join(missing)}")
        if unexpected:
            errors.append(f"assets/hook-events.json has unexpected supported events: {', '.join(unexpected)}")
    if set(conditions) != {"isMainSession", "hasCodeChange"}:
        errors.append("assets/hook-events.json must list Froggy conditions isMainSession and hasCodeChange")
    if set(actions) != {"bash", "command", "tool"}:
        errors.append("assets/hook-events.json must list Froggy actions bash, command, and tool")
    if manifest.get("plugin_name") != "opencode-froggy":
        errors.append("assets/hook-events.json must identify plugin_name as opencode-froggy")


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

    obsolete_files = [
        "templates/plugin-module.js.tmpl",
        "templates/plugin-module.ts.tmpl",
        "templates/lifecycle-action-plugin.ts.tmpl",
        "scripts/render_plugin_module.ts",
        "scripts/merge_package_json.ts",
    ]
    for rel_path in obsolete_files:
        if (skill_path / rel_path).exists():
            errors.append(f"Obsolete local-plugin generator file must not ship: {rel_path}")

    scaffold_script = skill_path / "scripts" / "scaffold_hooks.sh"
    if scaffold_script.exists():
        scaffold_content = scaffold_script.read_text(encoding="utf-8")
        for snippet in [
            "cleanup_legacy_plugin_scaffold",
            "opencode-froggy",
            "render_froggy_hooks.ts",
            ".opencode/hook/hooks.md",
            "scaffold_hooks",
        ]:
            if snippet not in scaffold_content:
                errors.append(f"scaffold_hooks.sh missing Froggy migration snippet: {snippet}")

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
