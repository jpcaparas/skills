#!/usr/bin/env python3
"""Check packaging and eval schemas, not model behaviour. Requires PyYAML."""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re

import yaml


REQUIRED = (
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "agents/openai.yaml",
    "references/spike-protocol.md",
    "scripts/scrape_docs.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "evals/evals.json",
    "evals/trigger-evals.json",
)
ASSERTION_TYPES = {"functional", "structural", "negative", "verification", "disclosure"}


def mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("expected a string-keyed object")
    return {key: item for key, item in value.items()}


def items(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("expected a list")
    return list(value)


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(root: Path) -> list[str]:
    errors = [f"missing {name}" for name in REQUIRED if not (root / name).is_file()]
    if errors:
        return errors
    try:
        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", skill, re.DOTALL)
        if match is None:
            raise ValueError("missing YAML frontmatter")
        frontmatter = mapping(yaml.safe_load(match.group(1)))
        if frontmatter.get("name") != root.name:
            errors.append("frontmatter name must match directory")
        if not nonempty(frontmatter.get("description")):
            errors.append("description must be non-empty")
        if frontmatter.get("disable-model-invocation") is not True:
            errors.append("Claude manual invocation must be enabled")
        if len(skill.splitlines()) > 500:
            errors.append("SKILL.md exceeds 500 lines")

        manifest = mapping(
            yaml.safe_load((root / "agents/openai.yaml").read_text(encoding="utf-8"))
        )
        if (
            mapping(manifest.get("policy")).get("allow_implicit_invocation")
            is not False
        ):
            errors.append("Codex implicit invocation must be disabled")
        metadata = mapping(
            json.loads((root / "metadata.json").read_text(encoding="utf-8"))
        )
        if (
            metadata.get("name") != root.name
            or metadata.get("entrypoint") != "SKILL.md"
        ):
            errors.append("metadata identity differs from canonical skill")

        for path in [root / "SKILL.md", *root.glob("references/*.md")]:
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(((?:references|scripts)/[^)]+)\)", text):
                resolved = (root / target).resolve()
                if (
                    not resolved.is_relative_to(root.resolve())
                    or not resolved.is_file()
                ):
                    errors.append(f"unresolved or escaping package reference: {target}")
        for path in root.glob("scripts/*.py"):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

        payload = mapping(
            json.loads((root / "evals/evals.json").read_text(encoding="utf-8"))
        )
        if payload.get("skill_name") != root.name:
            errors.append("eval skill_name must match directory")
        cases = items(payload.get("evals"))
        if not cases:
            errors.append("behavioural evals must not be empty")
        ids: set[int] = set()
        for value in cases:
            case = mapping(value)
            case_id = case.get("id")
            if type(case_id) is not int or case_id in ids:
                errors.append("eval IDs must be unique integers")
            else:
                ids.add(case_id)
            for field in ("name", "prompt", "expected_output"):
                if not nonempty(case.get(field)):
                    errors.append(f"eval {case_id}: missing {field}")
            assertions = items(case.get("assertions"))
            if not assertions:
                errors.append(f"eval {case_id}: no assertions")
            for value in assertions:
                assertion = mapping(value)
                if assertion.get("type") not in ASSERTION_TYPES or not nonempty(
                    assertion.get("text")
                ):
                    errors.append(f"eval {case_id}: invalid typed assertion")
            for relative in items(case.get("files", [])):
                if not isinstance(relative, str):
                    raise ValueError("eval fixture paths must be strings")
                resolved = (root / relative).resolve()
                if (
                    not resolved.is_relative_to(root.resolve())
                    or not resolved.is_file()
                ):
                    errors.append(
                        f"eval {case_id}: missing or escaping fixture {relative}"
                    )

        triggers = items(
            json.loads((root / "evals/trigger-evals.json").read_text(encoding="utf-8"))
        )
        outcomes: set[bool] = set()
        for value in triggers:
            trigger = mapping(value)
            expected = trigger.get("should_trigger")
            if not nonempty(trigger.get("query")) or type(expected) is not bool:
                errors.append("trigger requires query and boolean should_trigger")
            else:
                outcomes.add(expected)
        if outcomes != {True, False}:
            errors.append("trigger evals need positive and negative queries")
    except (OSError, ValueError, TypeError, SyntaxError, yaml.YAMLError) as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_path", type=Path)
    errors = validate(parser.parse_args().skill_path)
    print(json.dumps({"valid": not errors, "errors": errors}, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
