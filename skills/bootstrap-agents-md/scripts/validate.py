#!/usr/bin/env python3
"""Validate the bootstrap-agents-md skill package."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import sys


REQUIRED_FILES = {
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "agents/openai.yaml",
    "references/source-notes.md",
    "scripts/validate_agents_md.py",
    "scripts/test_validate_agents_md.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "skill-card.prompt.md",
    "skill-card.png",
}

ASSERTION_TYPES = {"functional", "structural", "disclosure", "negative", "verification"}
REQUIRED_TAGS = {"smoke", "edge", "negative", "replacement", "portability"}


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(?P<body>.*?)\n---\n", text, re.DOTALL)
    if not match:
        return {}
    parsed: dict[str, str] = {}
    for line in match.group("body").splitlines():
        item = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if item:
            parsed[item.group(1)] = item.group(2).strip().strip("\"'")
    return parsed


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate.py <skill-path>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for relative in sorted(REQUIRED_FILES):
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    skill_path = root / "SKILL.md"
    if skill_path.is_file():
        skill = skill_path.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(skill)
        if frontmatter.get("name") != root.name:
            errors.append("frontmatter name must match the skill directory")
        if not frontmatter.get("description"):
            errors.append("frontmatter description is required")
        if len(frontmatter.get("description", "")) > 450:
            errors.append("frontmatter description exceeds repository budget")
        if len(skill.splitlines()) > 500:
            errors.append("SKILL.md exceeds 500 lines")
        for required in [
            "## Output Contract",
            "## 1. Establish Scope and a Recoverable Baseline",
            "## 2. Inspect the Whole Project by Evidence Surface",
            "## 7. Explain the Replacement",
            "@AGENTS.md",
            "scripts/validate_agents_md.py",
        ]:
            if required not in skill:
                errors.append(f"SKILL.md missing required contract: {required}")
        if "TODO" in skill or "{{" in skill:
            errors.append("SKILL.md contains an unresolved placeholder")

    for path in sorted((root / "scripts").glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"python syntax error in {path.name}: {exc}")

    evals_path = root / "evals" / "evals.json"
    if evals_path.is_file():
        try:
            payload = json.loads(evals_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid evals JSON: {exc}")
        else:
            if payload.get("skill_name") != root.name:
                errors.append("eval skill_name must match the directory")
            cases = payload.get("evals", [])
            ids = [case.get("id") for case in cases]
            if len(ids) != len(set(ids)):
                errors.append("eval IDs must be unique")
            tags = {tag for case in cases for tag in case.get("tags", [])}
            missing_tags = sorted(REQUIRED_TAGS - tags)
            if missing_tags:
                errors.append(f"missing eval coverage tags: {', '.join(missing_tags)}")
            for case in cases:
                assertions = case.get("assertions", [])
                if not assertions:
                    errors.append(f"eval {case.get('id')} has no assertions")
                for assertion in assertions:
                    if assertion.get("type") not in ASSERTION_TYPES:
                        errors.append(f"eval {case.get('id')} has invalid assertion type")

    trigger_path = root / "evals" / "trigger-evals.json"
    if trigger_path.is_file():
        try:
            triggers = json.loads(trigger_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"invalid trigger eval JSON: {exc}")
        else:
            positives = sum(item.get("should_trigger") is True for item in triggers)
            negatives = sum(item.get("should_trigger") is False for item in triggers)
            if positives < 2 or negatives < 2:
                errors.append("trigger evals need at least two positive and two negative cases")

    result = {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {"skill_lines": len(skill_path.read_text(encoding="utf-8").splitlines()) if skill_path.is_file() else 0},
    }
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
