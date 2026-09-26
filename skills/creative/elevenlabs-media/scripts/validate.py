#!/usr/bin/env python3
"""Offline package integrity checks; no installed sibling skill is required."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

from elevenlabs_media import Json, MediaError, json_object, read_json


def validate(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    required = [
        "SKILL.md",
        "README.md",
        "AGENTS.md",
        "metadata.json",
        "evals/evals.json",
        "evals/trigger-evals.json",
        "evals/files/contracts.json",
        "references/evidence.md",
        "scripts/elevenlabs_media.py",
        "scripts/test_helper.py",
        "scripts/test_skill.py",
    ]
    for name in required:
        if not (root / name).is_file():
            errors.append(f"Missing {name}")
    if errors:
        return errors
    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = re.match(r"\A---\n(.*?)\n---\n", skill, flags=re.DOTALL)
    if (
        frontmatter is None
        or "name: elevenlabs-media\n" not in frontmatter.group(1) + "\n"
    ):
        errors.append("Canonical frontmatter name must be elevenlabs-media")
    if len(skill.splitlines()) > 500:
        errors.append("Keep SKILL.md within the 500-line disclosure budget")
    for path in root.rglob("*.md"):
        content = path.read_text(encoding="utf-8")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            if not resolved.is_relative_to(root) or not resolved.is_file():
                errors.append(
                    f"Broken or escaping link: {path.relative_to(root)} -> {target}"
                )
    for path in (root / "scripts").glob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"Python syntax: {path.name}: {exc.msg}")
    metadata = json_object(read_json(root / "metadata.json"))
    if (
        metadata.get("name") != "elevenlabs-media"
        or metadata.get("entrypoint") != "SKILL.md"
    ):
        errors.append("Metadata identity/entrypoint mismatch")
    suite = json_object(read_json(root / "evals/evals.json"))
    if suite.get("skill_name") != "elevenlabs-media":
        errors.append("Eval skill identity mismatch")
    cases = suite.get("evals")
    if not isinstance(cases, list) or not cases:
        errors.append("Behavioral scenarios must not be empty")
    else:
        ids: set[int] = set()
        for case in cases:
            case = json_object(case)
            case_id = case.get("id")
            if type(case_id) is not int or case_id in ids:
                errors.append("Eval IDs must be unique integers")
            else:
                ids.add(case_id)
            for key in ("name", "prompt", "expected_output"):
                if not isinstance(case.get(key), str) or not case[key]:
                    errors.append(f"Eval missing {key}")
            assertions = case.get("assertions")
            if not isinstance(assertions, list) or not assertions:
                errors.append("Every eval needs observable assertions")
            else:
                for assertion in assertions:
                    assertion = json_object(assertion)
                    if assertion.get("type") not in (
                        "functional",
                        "structural",
                        "negative",
                        "disclosure",
                    ):
                        errors.append("Unknown assertion type")
                    if (
                        not isinstance(assertion.get("text"), str)
                        or not assertion["text"]
                    ):
                        errors.append("Empty assertion")
            files = case.get("files", [])
            if not isinstance(files, list):
                errors.append("Eval files must be a list")
            else:
                for filename in files:
                    if not isinstance(filename, str):
                        errors.append("Eval fixture path must be text")
                        continue
                    fixture = (root / filename).resolve()
                    if not fixture.is_relative_to(root) or not fixture.is_file():
                        errors.append(f"Invalid fixture: {filename}")
    triggers: Json = read_json(root / "evals/trigger-evals.json")
    if not isinstance(triggers, list) or not triggers:
        errors.append("Trigger scenarios must not be empty")
    else:
        for trigger in triggers:
            trigger = json_object(trigger)
            if (
                not isinstance(trigger.get("query"), str)
                or type(trigger.get("should_trigger")) is not bool
            ):
                errors.append("Trigger needs query and boolean should_trigger")
    return errors


def main() -> int:
    root = (
        Path(sys.argv[1]) if len(sys.argv) == 2 else Path(__file__).resolve().parents[1]
    )
    try:
        errors = validate(root)
    except (OSError, ValueError, MediaError) as exc:
        print(f"Package validation failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    print(json.dumps({"valid": not errors, "errors": errors}))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
