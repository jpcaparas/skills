#!/usr/bin/env python3
"""
validate.py

Validate the scaffold-codex-hooks skill structure and its hook-event manifest.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


EXPECTED_EVENT_NAMES = {
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "Stop",
}
REQUIRED_OPERATIONAL_SCRIPTS = [
    "scripts/audit_project.sh",
    "scripts/check_hooks_feature.py",
    "scripts/merge_hooks_json.sh",
    "scripts/render_hooks_readme.sh",
    "scripts/scaffold_hooks.sh",
    "scripts/validate.py",
    "scripts/test_skill.py",
]
REQUIRED_SUPPORT_FILES = [
    "assets/hook-events.json",
    "templates/event-script.sh.tmpl",
    "templates/hook-plan.example.json",
    "references/project-analysis.md",
    "references/feature-flag.md",
    "references/hook-events.md",
    "references/scaffold-layout.md",
    "references/merge-strategy.md",
    "references/gotchas.md",
    "agents/openai.yaml",
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
    if not isinstance(events, list):
        errors.append("assets/hook-events.json: 'events' must be an array")
        return

    event_names = {event.get("name") for event in events}
    if event_names != EXPECTED_EVENT_NAMES:
        missing = sorted(EXPECTED_EVENT_NAMES - event_names)
        unexpected = sorted(event_names - EXPECTED_EVENT_NAMES)
        if missing:
            errors.append(f"assets/hook-events.json is missing events: {', '.join(missing)}")
        if unexpected:
            errors.append(f"assets/hook-events.json has unexpected events: {', '.join(unexpected)}")

    script_names = [event.get("script_name", "") for event in events]
    if "" in script_names:
        errors.append("assets/hook-events.json contains an event without a script_name")
    if len(set(script_names)) != len(script_names):
        errors.append("assets/hook-events.json contains duplicate script_name values")

    if manifest.get("async_supported") is not False:
        warnings.append("assets/hook-events.json should explicitly record async_supported=false")


def validate_skill(skill_path: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    skill_md_path = skill_path / "SKILL.md"
    if not skill_md_path.is_file():
        return {"valid": False, "errors": ["SKILL.md does not exist"], "warnings": warnings, "metrics": metrics}

    content = skill_md_path.read_text(encoding="utf-8")
    metrics["skill_md_lines"] = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    metrics["total_lines"] = metrics["skill_md_lines"]

    frontmatter, body = parse_frontmatter(content)
    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        name = frontmatter.get("name", "")
        if not name:
            errors.append("Frontmatter missing required 'name' field")
        elif name != skill_path.name:
            errors.append(f"name '{name}' does not match directory name '{skill_path.name}'")

        description = frontmatter.get("description", "")
        if not description:
            errors.append("Frontmatter missing required 'description' field")
        elif len(description) > 1024:
            errors.append(f"description exceeds 1024 chars ({len(description)} chars)")

    body_lines = body.count("\n") + (1 if body and not body.endswith("\n") else 0)
    if body_lines > 500:
        warnings.append(f"SKILL.md body is {body_lines} lines (target: under 500)")

    for ref in extract_file_references(content):
        if not (skill_path / ref).exists():
            errors.append(f"Referenced file does not exist: {ref}")

    required_dirs = ["references", "scripts", "templates", "evals", "assets", "agents"]
    for dirname in required_dirs:
        if not (skill_path / dirname).is_dir():
            errors.append(f"Missing required directory: {dirname}/")

    for rel_path in REQUIRED_OPERATIONAL_SCRIPTS + REQUIRED_SUPPORT_FILES:
        if not (skill_path / rel_path).exists():
            errors.append(f"Missing required file: {rel_path}")

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
