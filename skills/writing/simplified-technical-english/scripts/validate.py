#!/usr/bin/env python3
"""Validate the simplified-technical-english package contract."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys


SKILL_NAME = "simplified-technical-english"
REQUIRED_FILES = (
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "agents/openai.yaml",
    "references/descriptive-writing.md",
    "references/gotchas.md",
    "references/procedures-and-safety.md",
    "references/research-notes.md",
    "references/review-and-reporting.md",
    "references/terminology-and-verification.md",
    "templates/rewrite-report.md",
    "scripts/analyze_ste_surface.py",
    "scripts/test_skill.py",
    "scripts/validate.py",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "skill-card.png",
    "skill-card.prompt.md",
)
REQUIRED_TAGS = frozenset({"smoke", "edge", "negative", "disclosure"})
ALLOWED_ASSERTION_TYPES = frozenset(
    {"functional", "structural", "disclosure", "negative", "verification"}
)
LOCAL_REFERENCE_RE = re.compile(
    r"`((?:references|scripts|templates|evals|agents)/[^`\s]+)`"
)
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|TBD|FIXME)\b")


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_record(self) -> dict[str, object]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Parse the top-level scalar fields needed by this local validator."""

    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        closing = lines[1:].index("---") + 1
    except ValueError:
        return None

    fields: dict[str, str] = {}
    for line in lines[1:closing]:
        if not line or line[0].isspace():
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)", line)
        if not match:
            continue
        key, value = match.groups()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        fields[key] = value
    return fields


def validate_python(path: Path) -> str | None:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        return str(exc)
    return None


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_evals(root: Path, errors: list[str]) -> None:
    path = root / "evals" / "evals.json"
    if not path.is_file():
        return

    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid evals/evals.json: {exc}")
        return

    if not isinstance(payload, dict):
        errors.append("evals/evals.json must be an object")
        return
    if payload.get("skill_name") != SKILL_NAME:
        errors.append("evals/evals.json skill_name must match the package")

    cases = payload.get("evals")
    if not isinstance(cases, list) or not cases:
        errors.append("evals/evals.json must contain non-empty evals")
        return

    seen_ids: set[int] = set()
    tags: set[str] = set()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            errors.append(f"Eval {index} must be an object")
            continue

        case_id = case.get("id")
        if not isinstance(case_id, int) or case_id <= 0 or case_id in seen_ids:
            errors.append(f"Eval {index} has an invalid or duplicate id")
        else:
            seen_ids.add(case_id)

        assertions = case.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            errors.append(f"Eval {index} must contain assertions")
        else:
            for assertion in assertions:
                if not isinstance(assertion, dict):
                    errors.append(f"Eval {index} contains a non-object assertion")
                    continue
                assertion_type = assertion.get("type")
                if assertion_type not in ALLOWED_ASSERTION_TYPES:
                    errors.append(
                        f"Eval {index} has unsupported assertion type: {assertion_type}"
                    )
                if not isinstance(assertion.get("text"), str) or not assertion["text"].strip():
                    errors.append(f"Eval {index} has an empty assertion")

        case_tags = case.get("tags", [])
        if isinstance(case_tags, list):
            tags.update(tag for tag in case_tags if isinstance(tag, str))

        files = case.get("files", [])
        if isinstance(files, list):
            for relative in files:
                if not isinstance(relative, str):
                    errors.append(f"Eval {index} contains a non-string fixture path")
                    continue
                candidate = (root / relative).resolve()
                try:
                    candidate.relative_to(root.resolve())
                except ValueError:
                    errors.append(f"Eval {index} fixture escapes the package: {relative}")
                    continue
                if not candidate.is_file():
                    errors.append(f"Eval {index} fixture is missing: {relative}")

    missing_tags = sorted(REQUIRED_TAGS - tags)
    if missing_tags:
        errors.append(f"Missing eval coverage tags: {', '.join(missing_tags)}")


def validate_triggers(root: Path, errors: list[str]) -> None:
    path = root / "evals" / "trigger-evals.json"
    if not path.is_file():
        return

    try:
        payload = load_json(path)
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"Invalid evals/trigger-evals.json: {exc}")
        return

    if not isinstance(payload, list) or not payload:
        errors.append("evals/trigger-evals.json must be a non-empty array")
        return

    outcomes: set[bool] = set()
    queries: set[str] = set()
    for index, case in enumerate(payload, start=1):
        if not isinstance(case, dict) or set(case) != {"query", "should_trigger"}:
            errors.append(f"Trigger eval {index} must contain query and should_trigger only")
            continue
        query = case.get("query")
        outcome = case.get("should_trigger")
        if not isinstance(query, str) or not query.strip() or query in queries:
            errors.append(f"Trigger eval {index} has an empty or duplicate query")
        else:
            queries.add(query)
        if not isinstance(outcome, bool):
            errors.append(f"Trigger eval {index} should_trigger must be Boolean")
        else:
            outcomes.add(outcome)

    if outcomes != {False, True}:
        errors.append("Trigger evals must contain positive and negative cases")


def validate_skill(skill_path: str | Path) -> ValidationResult:
    root = Path(skill_path).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if root.name != SKILL_NAME:
        errors.append(f"Skill directory must be named {SKILL_NAME}")

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"Missing required file: {relative}")

    skill_path_resolved = root / "SKILL.md"
    if skill_path_resolved.is_file():
        text = skill_path_resolved.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(text)
        if frontmatter is None:
            errors.append("SKILL.md must have closed YAML frontmatter")
        else:
            if frontmatter.get("name") != SKILL_NAME:
                errors.append("SKILL.md frontmatter name must match the package")
            description = frontmatter.get("description", "")
            if not description:
                errors.append("SKILL.md frontmatter description is required")
            if len(description) > 450:
                errors.append("SKILL.md description exceeds the repository budget")

        if len(text.splitlines()) > 500:
            errors.append("SKILL.md exceeds 500 lines")
        if PLACEHOLDER_RE.search(text):
            errors.append("SKILL.md contains an unresolved placeholder")

    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if PLACEHOLDER_RE.search(text) and path.name != "rewrite-report.md":
            errors.append(f"Unresolved placeholder found in {path.relative_to(root)}")
        for relative in LOCAL_REFERENCE_RE.findall(text):
            if not (root / relative).exists():
                errors.append(
                    f"Broken local reference in {path.relative_to(root)}: {relative}"
                )

    for path in sorted((root / "scripts").glob("*.py")) if (root / "scripts").is_dir() else []:
        syntax_error = validate_python(path)
        if syntax_error:
            errors.append(f"Python syntax error in {path.relative_to(root)}: {syntax_error}")

    metadata_path = root / "metadata.json"
    if metadata_path.is_file():
        try:
            metadata = load_json(metadata_path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid metadata.json: {exc}")
        else:
            if not isinstance(metadata, dict) or metadata.get("version") != "1.0.0":
                errors.append("metadata.json must be an object with version 1.0.0")

    validate_evals(root, errors)
    validate_triggers(root, errors)

    for directory in ("agents", "evals", "references", "scripts", "templates"):
        path = root / directory
        if path.is_dir() and not any(candidate.is_file() for candidate in path.rglob("*")):
            errors.append(f"Support directory is empty: {directory}/")

    return ValidationResult(errors=tuple(errors), warnings=tuple(warnings))


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        return 2

    result = validate_skill(sys.argv[1])
    print(json.dumps(result.as_record(), indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
