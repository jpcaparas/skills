#!/usr/bin/env python3
"""Validate this portable package and eval schemas, not agent behaviour.

Requires Python 3.11+ and PyYAML. Exit 0 on success, 1 for invalid packaging,
or 2 for CLI usage errors. Reads local files only; never runs eval prompts.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

import yaml

REQUIRED = (
    "SKILL.md",
    "README.md",
    "references/behaviour-harness.md",
    "references/production-data.md",
    "references/plan-and-handoff.md",
    "evals/README.md",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "scripts/validate.py",
    "scripts/test_skill.py",
)
ASSERTION_TYPES = {"functional", "structural", "negative", "verification", "disclosure"}


def mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError("expected a string-keyed object")
    return {key: item for key, item in value.items()}


def items(value: object) -> list[object]:
    if not isinstance(value, list):
        raise TypeError("expected a list")
    return list(value)


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def package_file(root: Path, relative: str) -> bool:
    path = Path(relative)
    resolved = (root / path).resolve()
    return (
        not path.is_absolute() and resolved.is_relative_to(root) and resolved.is_file()
    )


def validate(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    try:
        errors.extend(
            f"missing or escaping file: {name}"
            for name in REQUIRED
            if not package_file(root, name)
        )
        if errors:
            return errors

        skill = (root / "SKILL.md").read_text(encoding="utf-8")
        match = re.match(r"\A---\n(.*?)\n---\n", skill, re.DOTALL)
        if match is None:
            raise ValueError("missing YAML frontmatter")
        frontmatter = mapping(yaml.safe_load(match.group(1)))
        if frontmatter.get("name") != root.name:
            errors.append("frontmatter name must match directory")
        description = frontmatter.get("description")
        if not isinstance(description, str) or not 0 < len(description.strip()) <= 450:
            errors.append("description must contain 1–450 characters")
        if len(skill.splitlines()) > 500:
            errors.append("SKILL.md exceeds 500 lines")

        # Runtime links are package-root relative; fixture paths are checked below.
        for path in (
            root / "SKILL.md",
            root / "README.md",
            *root.glob("references/*.md"),
        ):
            for relative in re.findall(
                r"\]\(((?:references|scripts|evals)/[^)#]+)(?:#[^)]*)?\)",
                path.read_text(encoding="utf-8"),
            ):
                if not package_file(root, relative):
                    errors.append(f"missing or escaping reference: {relative}")
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
            if type(case_id) is not int or case_id < 1 or case_id in ids:
                errors.append("eval IDs must be unique positive integers")
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
                kind = assertion.get("type")
                if (
                    not isinstance(kind, str)
                    or kind not in ASSERTION_TYPES
                    or not nonempty(assertion.get("text"))
                ):
                    errors.append(f"eval {case_id}: invalid typed assertion")
            for relative in items(case.get("files", [])):
                if not isinstance(relative, str) or not package_file(root, relative):
                    errors.append(f"eval {case_id}: missing or escaping fixture")

        outcomes: set[bool] = set()
        triggers = items(
            json.loads((root / "evals/trigger-evals.json").read_text(encoding="utf-8"))
        )
        for value in triggers:
            trigger = mapping(value)
            expected = trigger.get("should_trigger")
            if not nonempty(trigger.get("query")) or type(expected) is not bool:
                errors.append("trigger requires query and boolean should_trigger")
            else:
                outcomes.add(expected)
        if outcomes != {True, False}:
            errors.append("trigger evals need positive and negative queries")
    except (
        OSError,
        ValueError,
        TypeError,
        RuntimeError,
        SyntaxError,
        yaml.YAMLError,
    ) as exc:
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
