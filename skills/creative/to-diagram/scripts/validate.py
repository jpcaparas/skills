#!/usr/bin/env python3
"""Validate the to-diagram release package and its owned contracts."""

from __future__ import annotations

import ast
from dataclasses import dataclass
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
    "evals/evals.json",
    "evals/trigger-evals.json",
    "scripts/render_diagram.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "skill-card.prompt.md",
    "skill-card.png",
}
REQUIRED_HEADINGS = {
    "## Invocation",
    "## Workflow",
    "## Quality Gate",
    "## Helper",
}
REQUIRED_CONTRACTS = {
    "exactly two durable deliverables": "two-file output contract",
    "exactly one fenced `mermaid` block": "single Mermaid source contract",
    "Ask one focused clarification": "ambiguity boundary",
    "do not turn correlation into causation": "scientific evidence boundary",
    "Inspect the PNG": "visual verification contract",
    "Do not create a separate `.mmd`": "no-sidecar contract",
    "@mermaid-js/mermaid-cli@^11": "compatible Mermaid CLI range",
}
DESCRIPTION_TERMS = {
    "engineering",
    "scientific",
    "general",
    "mermaid",
    "markdown",
    "png",
    "/to-diagram",
}
ASSERTION_TYPES = {"functional", "structural", "negative", "verification", "disclosure"}
REQUIRED_EVAL_TAGS = {"smoke", "edge", "negative", "engineering", "scientific", "general", "export", "invocation"}
MACHINE_PATHS = (
    re.compile(r"/Users/"),
    re.compile(r"/home/(?!readable-placeholder)"),
    re.compile(r"[A-Za-z]:\\\\"),
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
        if item is not None:
            fields[item.group(1)] = item.group(2).strip().strip("\"'")
    return fields


def load_json(path: Path, errors: list[str]) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{path.relative_to(path.parents[1])} is invalid JSON: {exc}")
        return None


def validate_behavior_evals(root: Path, errors: list[str]) -> int:
    payload = load_json(root / "evals" / "evals.json", errors)
    if not isinstance(payload, dict):
        errors.append("evals/evals.json must contain an object")
        return 0
    if payload.get("skill_name") != root.name:
        errors.append("eval skill_name must match the skill directory")

    cases = payload.get("evals")
    if not isinstance(cases, list) or len(cases) < 8:
        errors.append("evals/evals.json requires at least eight behavioral cases")
        return 0

    ids: set[int] = set()
    tags: set[str] = set()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"eval {index} must be an object")
            continue
        case_id = case.get("id")
        if not isinstance(case_id, int) or case_id in ids:
            errors.append(f"eval {index} must have a unique integer ID")
        else:
            ids.add(case_id)
        for field in ("name", "prompt", "expected_output"):
            value = case.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"eval {case_id or index} requires non-empty {field}")
        assertions = case.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            errors.append(f"eval {case_id or index} requires typed assertions")
        else:
            for assertion in assertions:
                if not isinstance(assertion, dict):
                    errors.append(f"eval {case_id or index} has a non-object assertion")
                    continue
                if assertion.get("type") not in ASSERTION_TYPES:
                    errors.append(f"eval {case_id or index} has an invalid assertion type")
                text = assertion.get("text")
                if not isinstance(text, str) or not text.strip():
                    errors.append(f"eval {case_id or index} has an empty assertion")
        case_tags = case.get("tags")
        if isinstance(case_tags, list):
            tags.update(tag for tag in case_tags if isinstance(tag, str))

    missing_tags = sorted(REQUIRED_EVAL_TAGS - tags)
    if missing_tags:
        errors.append("missing eval coverage tags: " + ", ".join(missing_tags))
    return len(cases)


def validate_trigger_evals(root: Path, errors: list[str]) -> int:
    payload = load_json(root / "evals" / "trigger-evals.json", errors)
    if not isinstance(payload, list):
        errors.append("evals/trigger-evals.json must contain a list")
        return 0

    positives = 0
    negatives = 0
    direct_invocation = False
    for index, case in enumerate(payload, start=1):
        if not isinstance(case, dict) or not isinstance(case.get("query"), str):
            errors.append(f"trigger {index} requires a query")
            continue
        should_trigger = case.get("should_trigger")
        if should_trigger is True:
            positives += 1
            direct_invocation = direct_invocation or "/to-diagram" in case["query"]
        elif should_trigger is False:
            negatives += 1
        else:
            errors.append(f"trigger {index} requires a boolean should_trigger")

    if positives < 5 or negatives < 5:
        errors.append("trigger evals require at least five positive and five negative cases")
    if not direct_invocation:
        errors.append("trigger evals require a direct /to-diagram invocation")
    return len(payload)


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
        description = frontmatter.get("description", "")
        missing_description_terms = sorted(
            term for term in DESCRIPTION_TERMS if term not in description.lower()
        )
        if missing_description_terms:
            errors.append(
                "frontmatter description is missing: "
                + ", ".join(missing_description_terms)
            )
        if skill_lines > 500:
            errors.append("SKILL.md exceeds 500 lines")
        if any(pattern.search(skill) for pattern in MACHINE_PATHS):
            errors.append("SKILL.md contains a machine-specific path")
        for heading in sorted(REQUIRED_HEADINGS):
            if heading not in skill:
                errors.append(f"SKILL.md missing required heading: {heading}")
        for phrase, contract in REQUIRED_CONTRACTS.items():
            if phrase not in skill:
                errors.append(f"SKILL.md missing {contract}: {phrase}")
        if re.search(r"\b(?:TODO|TBD|FIXME)\b", skill):
            errors.append("SKILL.md contains an unresolved authoring marker")

    metadata_path = root / "metadata.json"
    if metadata_path.is_file():
        metadata = load_json(metadata_path, errors)
        if not isinstance(metadata, dict):
            errors.append("metadata.json must contain an object")
        else:
            expected = {
                "name": root.name,
                "display_name": "To Diagram",
                "version": "1.0.0",
                "license": "MIT",
                "entrypoint": "SKILL.md",
            }
            for key, value in expected.items():
                if metadata.get(key) != value:
                    errors.append(f"metadata.json field {key} must equal {value!r}")

    manifest_path = root / "agents" / "openai.yaml"
    if manifest_path.is_file():
        manifest = manifest_path.read_text(encoding="utf-8")
        for fragment in (
            'display_name: "To Diagram"',
            'short_description: "Clarify a complex process as Mermaid and PNG"',
            "$to-diagram",
        ):
            if fragment not in manifest:
                errors.append(f"agents/openai.yaml is missing: {fragment}")

    render_path = root / "scripts" / "render_diagram.py"
    if render_path.is_file():
        renderer = render_path.read_text(encoding="utf-8")
        for fragment in (
            '@mermaid-js/mermaid-cli@^11',
            'TemporaryDirectory(',
            '"neutral"',
            '"white"',
            'PNG_SIGNATURE',
        ):
            if fragment not in renderer:
                errors.append(f"render_diagram.py is missing contract: {fragment}")

    for path in sorted((root / "scripts").glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"python syntax error in {path.name}: {exc}")

    prompt_path = root / "skill-card.prompt.md"
    if prompt_path.is_file():
        prompt = prompt_path.read_text(encoding="utf-8")
        if "`to-diagram` README skill badge" not in prompt:
            errors.append("skill-card.prompt.md must identify to-diagram")
    card_path = root / "skill-card.png"
    if card_path.is_file() and card_path.stat().st_size < 10_000:
        errors.append("skill-card.png is suspiciously small")

    eval_count = validate_behavior_evals(root, errors)
    trigger_count = validate_trigger_evals(root, errors)
    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        metrics={
            "skill_lines": skill_lines,
            "evals": eval_count,
            "triggers": trigger_count,
        },
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
