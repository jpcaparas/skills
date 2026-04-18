#!/usr/bin/env python3
"""Validate the travel-plan-spreadsheet-generator skill structure and packaging."""

from __future__ import annotations

import json
import os
import py_compile
import re
import sys
from pathlib import Path

REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "references/workbook-spec.md",
    "references/intake-protocol.md",
    "references/research-policy.md",
    "references/trip-model.md",
    "references/mapping-rules.md",
    "references/gotchas.md",
    "references/cross-harness-notes.md",
    "scripts/build_workbook.py",
    "scripts/validate_workbook.py",
    "scripts/example_trip_model.json",
    "scripts/render_check.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "templates/trip_model_schema.json",
    "templates/workbook_template_spec.yaml",
    "evals/evals.json",
    "assets/palette.json",
    "agents/reviewer.md",
]

REQUIRED_ALIASES = [
    "travel-plan-generator",
    "travel itinerary spreadsheet",
    "travel planner xlsx",
    "trip spreadsheet",
    "itinerary workbook",
    "travel prep spreadsheet",
    "travel shopping tracker",
    "holiday itinerary spreadsheet",
    "conference travel spreadsheet",
]

NEGATIVE_TRIGGER_SNIPPETS = [
    "plain prose itineraries",
    "simple travel recommendations",
    "casual things-to-do chat",
    "calendar scheduling without workbook generation",
]


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---"):
        raise ValueError("SKILL.md has no YAML frontmatter")
    end = content.find("\n---", 3)
    if end == -1:
        raise ValueError("SKILL.md frontmatter is not closed")
    frontmatter_text = content[3:end].strip()
    body = content[end + 4 :].lstrip()
    frontmatter: dict[str, str] = {}
    for line in frontmatter_text.splitlines():
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, value = line.split(":", 1)
        value = value.strip().strip('"').strip("'")
        frontmatter[key.strip()] = value
    return frontmatter, body


def extract_file_references(content: str) -> list[str]:
    refs: list[str] = []
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    for match in re.finditer(r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`", stripped):
        refs.append(match.group(1))
    return sorted(set(refs))


def validate_skill(skill_path: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, object] = {}

    for relative in REQUIRED_FILES:
        if not (skill_path / relative).exists():
            errors.append(f"Missing required file: {relative}")

    skill_content = (skill_path / "SKILL.md").read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(skill_content)
    metrics["skill_md_lines"] = body.count("\n") + 1
    if frontmatter.get("name") != skill_path.name:
        errors.append(f"Frontmatter name must match directory name: {skill_path.name}")
    description = frontmatter.get("description", "")
    if not description:
        errors.append("Frontmatter description is required")
    for alias in REQUIRED_ALIASES:
        if alias not in description:
            errors.append(f"Missing trigger phrase in frontmatter description: {alias}")
    for snippet in NEGATIVE_TRIGGER_SNIPPETS:
        if snippet not in description:
            errors.append(f"Missing negative trigger in frontmatter description: {snippet}")
    if "/home/oai/skills/spreadsheets/SKILL.md" not in skill_content:
        errors.append("SKILL.md must mention /home/oai/skills/spreadsheets/SKILL.md for Codex-style environments")
    if metrics["skill_md_lines"] and metrics["skill_md_lines"] > 500:
        errors.append(f"SKILL.md body exceeds 500 lines: {metrics['skill_md_lines']}")

    for relative in extract_file_references(skill_content):
        if not (skill_path / relative).exists():
            errors.append(f"Broken cross-reference in SKILL.md: {relative}")

    metadata = json.loads((skill_path / "metadata.json").read_text(encoding="utf-8"))
    if "tags" not in metadata or not metadata["tags"]:
        errors.append("metadata.json should include tags")

    example_model = json.loads((skill_path / "scripts" / "example_trip_model.json").read_text(encoding="utf-8"))
    if "trip_title" not in example_model or "daily_rows" not in example_model:
        errors.append("example_trip_model.json is missing key fields")

    evals = json.loads((skill_path / "evals" / "evals.json").read_text(encoding="utf-8"))
    eval_cases = evals.get("evals", [])
    if len(eval_cases) < 7:
        errors.append("evals/evals.json should contain at least 7 eval cases")
    seen_ids: set[int] = set()
    for case in eval_cases:
        case_id = case.get("id")
        if case_id in seen_ids:
            errors.append(f"Duplicate eval id: {case_id}")
        seen_ids.add(case_id)

    yaml_text = (skill_path / "templates" / "workbook_template_spec.yaml").read_text(encoding="utf-8")
    for required_snippet in ("Overview", "Bookings", "Daily Plan", "Sources"):
        if required_snippet not in yaml_text:
            errors.append(f"workbook_template_spec.yaml is missing: {required_snippet}")

    for script_path in (skill_path / "scripts").glob("*.py"):
        try:
            py_compile.compile(str(script_path), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"Python syntax error in {script_path.name}: {exc.msg}")

    return {"valid": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        raise SystemExit(1)
    skill_path = Path(sys.argv[1]).expanduser().resolve()
    result = validate_skill(skill_path)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
