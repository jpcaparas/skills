#!/usr/bin/env python3
"""Validate the make-my-code-flirtatious skill package."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import json
from pathlib import Path
import re
import struct
import sys


REQUIRED_FILES = {
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "skill-card.prompt.md",
    "skill-card.png",
}
REQUIRED_HEADINGS = {
    "## Invocation Boundary",
    "## Workflow",
    "## Voice Contract",
    "## Guardrails",
    "## Pre-Send Gate",
}
REQUIRED_CONTRACTS = {
    "Technical truth outranks the mood": "technical-fidelity priority",
    "Use this skill only when": "explicit style invocation",
    "Do not invent retries": "evidence boundary",
    "Flirt with the code, not the user": "code-only flirtation target",
    "Never make the response sexually explicit": "non-graphic boundary",
    "high-stakes code, restrain the style": "high-stakes restraint",
}
ASSERTION_TYPES = {"functional", "structural", "negative", "verification", "disclosure"}
REQUIRED_EVAL_TAGS = {"smoke", "edge", "negative", "safety", "evidence", "style", "invocation"}
MACHINE_PATHS = (re.compile(r"/Users/"), re.compile(r"/home/"), re.compile(r"[A-Za-z]:\\\\"))
EXPECTED_DESCRIPTION = (
    "Explains code flirtatiously without losing accuracy. Use for flirty or sultry code "
    "explanations; skip ordinary explanations, code edits, and explicit sexual content."
)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
    metrics: dict[str, int]

    def to_json_object(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics,
        }


def parse_frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"^---\n(?P<body>.*?)\n---\n", text, re.DOTALL)
    if match is None:
        return {}
    fields: dict[str, str] = {}
    for line in match.group("body").splitlines():
        item = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if item:
            fields[item.group(1)] = item.group(2).strip().strip("\"'")
    return fields


def load_json(path: Path, errors: list[str]) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.name} is invalid JSON: {exc}")
        return None


def validate_evals(root: Path, errors: list[str]) -> int:
    path = root / "evals" / "evals.json"
    if not path.is_file():
        return 0
    payload = load_json(path, errors)
    if not isinstance(payload, dict):
        errors.append("evals.json must contain an object")
        return 0
    if payload.get("skill_name") != root.name:
        errors.append("eval skill_name must match the skill directory")
    cases = payload.get("evals")
    if not isinstance(cases, list) or len(cases) < 6:
        errors.append("evals.json requires at least six behavioral cases")
        return 0

    seen_ids: set[int] = set()
    tags: set[str] = set()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"eval {index} must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, int) or isinstance(case_id, bool) or case_id in seen_ids:
            errors.append(f"eval {index} must have a unique integer ID")
        else:
            seen_ids.add(case_id)
        for field in ("name", "prompt", "expected_output"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                errors.append(f"eval {case_id or index} requires non-empty {field}")
        assertions = case.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            errors.append(f"eval {case_id or index} requires typed assertions")
        else:
            for assertion in assertions:
                if not isinstance(assertion, dict) or assertion.get("type") not in ASSERTION_TYPES:
                    errors.append(f"eval {case_id or index} has an invalid assertion type")
                elif not isinstance(assertion.get("text"), str) or not assertion["text"].strip():
                    errors.append(f"eval {case_id or index} has an empty assertion")
        case_tags = case.get("tags")
        if isinstance(case_tags, list):
            tags.update(tag for tag in case_tags if isinstance(tag, str))

    missing_tags = sorted(REQUIRED_EVAL_TAGS - tags)
    if missing_tags:
        errors.append("missing eval coverage tags: " + ", ".join(missing_tags))
    return len(cases)


def validate_triggers(root: Path, errors: list[str]) -> int:
    path = root / "evals" / "trigger-evals.json"
    if not path.is_file():
        return 0
    payload = load_json(path, errors)
    if not isinstance(payload, list):
        errors.append("trigger-evals.json must contain a list")
        return 0

    positives = 0
    negatives = 0
    positive_queries: list[str] = []
    for index, case in enumerate(payload, start=1):
        if not isinstance(case, dict) or set(case) != {"query", "should_trigger"}:
            errors.append(f"trigger {index} requires exactly query and should_trigger")
            continue
        if not isinstance(case["query"], str) or not case["query"].strip():
            errors.append(f"trigger {index} requires a non-empty query")
            continue
        if case["should_trigger"] is True:
            positives += 1
            positive_queries.append(case["query"])
        elif case["should_trigger"] is False:
            negatives += 1
        else:
            errors.append(f"trigger {index} requires a boolean should_trigger")

    if positives < 5 or negatives < 5:
        errors.append("trigger evals require at least five positive and five negative cases")
    if not any("make-my-code-flirtatious" in query for query in positive_queries):
        errors.append("trigger evals require a direct named invocation")
    return len(payload)


def validate_png(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        return
    data = path.read_bytes()
    if len(data) < 10_000:
        errors.append("skill-card.png is suspiciously small")
        return
    if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
        errors.append("skill-card.png must be a valid PNG")
        return
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) != (1024, 576):
        errors.append("skill-card.png must be 1024x576")


def validate_skill(root: Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    for relative in sorted(REQUIRED_FILES):
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    skill_path = root / "SKILL.md"
    skill_lines = 0
    if skill_path.is_file():
        skill = skill_path.read_text(encoding="utf-8")
        skill_lines = len(skill.splitlines())
        frontmatter = parse_frontmatter(skill)
        if frontmatter.get("name") != root.name:
            errors.append("frontmatter name must match the skill directory")
        if frontmatter.get("description") != EXPECTED_DESCRIPTION:
            errors.append("frontmatter description must preserve the invocation contract")
        if skill_lines > 500:
            errors.append("SKILL.md exceeds 500 lines")
        if any(pattern.search(skill) for pattern in MACHINE_PATHS):
            errors.append("SKILL.md contains a machine-specific path")
        for heading in sorted(REQUIRED_HEADINGS):
            if heading not in skill:
                errors.append(f"SKILL.md missing required contract: {heading}")
        for phrase, contract in REQUIRED_CONTRACTS.items():
            if phrase not in skill:
                errors.append(f"SKILL.md missing {contract}: {phrase}")
        if "TODO" in skill or "{{" in skill:
            errors.append("SKILL.md contains an unresolved placeholder")

    metadata_path = root / "metadata.json"
    if metadata_path.is_file():
        metadata = load_json(metadata_path, errors)
        if not isinstance(metadata, dict):
            errors.append("metadata.json must contain an object")
        else:
            expected = {
                "name": root.name,
                "display_name": "Make My Code Flirtatious",
                "version": "1.0.0",
                "license": "MIT",
                "entrypoint": "SKILL.md",
            }
            for key, value in expected.items():
                if metadata.get(key) != value:
                    errors.append(f"metadata.json field {key} must equal {value!r}")

    prompt_path = root / "skill-card.prompt.md"
    if prompt_path.is_file():
        prompt = prompt_path.read_text(encoding="utf-8")
        if "`make-my-code-flirtatious` README skill badge" not in prompt:
            errors.append("skill-card.prompt.md must identify make-my-code-flirtatious")
    validate_png(root / "skill-card.png", errors)

    for path in sorted((root / "scripts").glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"python syntax error in {path.name}: {exc}")

    eval_count = validate_evals(root, errors)
    trigger_count = validate_triggers(root, errors)
    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        metrics={"skill_lines": skill_lines, "evals": eval_count, "triggers": trigger_count},
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate.py <skill-path>", file=sys.stderr)
        return 2
    result = validate_skill(Path(sys.argv[1]).resolve())
    print(json.dumps(result.to_json_object(), indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
