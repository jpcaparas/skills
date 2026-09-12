#!/usr/bin/env python3
"""
validate.py

Validate the copilot harness component of scaffold-hooks and event manifest.
"""

from __future__ import annotations

import json
import re
import sys
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
REQUIRED_OPERATIONAL_SCRIPTS = [
    "scripts/audit_project.sh",
    "scripts/merge_hooks_file.sh",
    "scripts/render_hooks_readme.sh",
    "scripts/scaffold_hooks.sh",
    "scripts/verify_docs.py",
]
REQUIRED_SUPPORT_FILES = [
    "assets/hook-events.json",
    "templates/event-script.sh.tmpl",
    "templates/hook-plan.example.json",
    "references/project-analysis.md",
    "references/hook-events.md",
    "references/scaffold-layout.md",
    "references/reusable-scripts.md",
    "references/merge-strategy.md",
    "references/gotchas.md",
]
REQUIRED_DOC_URLS = [
    "https://docs.github.com/en/copilot/concepts/agents/hooks",
    "https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks",
    "https://docs.github.com/en/copilot/reference/hooks-reference",
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

    event_names = {event.get("name", "") for event in events}
    if event_names != EXPECTED_EVENT_NAMES:
        missing = sorted(EXPECTED_EVENT_NAMES - event_names)
        unexpected = sorted(event_names - EXPECTED_EVENT_NAMES)
        if missing:
            errors.append(f"assets/hook-events.json missing events: {', '.join(missing)}")
        if unexpected:
            errors.append(f"assets/hook-events.json has unexpected events: {', '.join(unexpected)}")

    script_names = [event.get("script_name", "") for event in events]
    if "" in event_names:
        errors.append("assets/hook-events.json contains an event without a name")
    if "" in script_names:
        errors.append("assets/hook-events.json contains an event without a script_name")
    if len(set(script_names)) != len(script_names):
        errors.append("assets/hook-events.json contains duplicate script_name values")

    verified_from = manifest.get("verified_from", [])
    for url in REQUIRED_DOC_URLS:
        if url not in verified_from:
            errors.append(f"assets/hook-events.json missing verified source: {url}")

    notes = "\n".join(manifest.get("notes", []))
    for snippet in [
        ".github/hooks/*.json",
        "version: 1",
        "preToolUse",
        "permissionRequest",
        "exit code 2",
        "Matchers are regexes",
    ]:
        if snippet not in notes:
            errors.append(f"assets/hook-events.json notes missing: {snippet}")

    if not manifest.get("verified_on"):
        warnings.append("assets/hook-events.json has no verified_on date")


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
        if ref.startswith("{{ skill:"):
            continue
        if not (skill_path / ref).exists():
            errors.append(f"Referenced file does not exist: {ref}")

    required_dirs = ["references", "scripts", "templates", "assets"]
    for dirname in required_dirs:
        dir_path = skill_path / dirname
        if not dir_path.is_dir():
            errors.append(f"Missing required directory: {dirname}/")

    for rel_path in REQUIRED_OPERATIONAL_SCRIPTS + REQUIRED_SUPPORT_FILES:
        if not (skill_path / rel_path).exists():
            errors.append(f"Missing required file: {rel_path}")

    validate_manifest(skill_path, errors, warnings)

    plan_path = skill_path / "templates" / "hook-plan.example.json"
    if plan_path.is_file():
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            if plan.get("hooks_target") != ".github/hooks/copilot-hooks.json":
                errors.append("templates/hook-plan.example.json must target .github/hooks/copilot-hooks.json")
            if plan.get("managed_root") != ".github/copilot/hooks/generated":
                errors.append("templates/hook-plan.example.json must use .github/copilot/hooks/generated")
        except json.JSONDecodeError as exc:
            errors.append(f"templates/hook-plan.example.json is not valid JSON: {exc}")

    refs_dir = skill_path / "references"
    if refs_dir.is_dir():
        for ref_path in refs_dir.rglob("*"):
            if ref_path.is_file():
                metrics["reference_count"] += 1
                metrics["total_lines"] += ref_path.read_text(encoding="utf-8").count("\n") + 1

    valid = not errors
    return {
        "valid": valid,
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
