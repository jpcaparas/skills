#!/usr/bin/env python3
"""Validate the portable package contract for oneshot-timeline."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
from typing import TypeAlias, cast
from urllib.parse import unquote


JsonValue: TypeAlias = str | int | float | bool | None | list["JsonValue"] | dict[str, "JsonValue"]


REQUIRED_FILES = (
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "references/media.md",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "evals/files/dns-facts.md",
    "evals/files/leaseco-evidence.md",
    "scripts/validate.py",
    "scripts/test_skill.py",
)
ASSERTION_TYPES = frozenset(
    {"structural", "functional", "verification", "negative", "disclosure"}
)
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


@dataclass(frozen=True, slots=True)
class ValidationResult:
    errors: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.errors

    def as_json(self) -> dict[str, object]:
        return {"valid": self.valid, "errors": list(self.errors)}


def read_text(path: Path, errors: list[str], label: str) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"Cannot read {label}: {exc}")
        return None


def load_json(path: Path, errors: list[str], label: str) -> JsonValue:
    text = read_text(path, errors, label)
    if text is None:
        return None
    try:
        # The standard decoder produces these recursive JSON types; callers
        # narrow the document shape before accessing package-specific fields.
        return cast(JsonValue, json.loads(text))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in {label}: line {exc.lineno}, column {exc.colno}")
        return None


def parse_frontmatter(text: str) -> dict[str, str] | None:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return None
    try:
        end = lines.index("---", 1)
    except ValueError:
        return None
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if not line or line[0].isspace():
            continue
        match = re.fullmatch(r"([A-Za-z][A-Za-z0-9_-]*):\s*(.+)", line)
        if match is None:
            continue
        value = match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        fields[match.group(1)] = value
    return fields


def contained_file(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError, RuntimeError):
        return False
    return candidate.is_file()


def validate_markdown_links(root: Path, errors: list[str]) -> None:
    for path in sorted(root.rglob("*.md")):
        if not contained_file(root, path):
            errors.append(f"Markdown file escapes package through symlink: {path.relative_to(root)}")
            continue
        text = read_text(path, errors, str(path.relative_to(root)))
        if text is None:
            continue
        for match in MARKDOWN_LINK.finditer(text):
            parts = match.group(1).strip().split(maxsplit=1)
            if not parts:
                errors.append(f"Empty Markdown reference: {path.relative_to(root)}")
                continue
            target = parts[0].strip("<>")
            target = target.split("#", 1)[0].split("?", 1)[0]
            if not target or re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            candidate = path.parent / unquote(target)
            if not contained_file(root, candidate):
                errors.append(
                    f"Local Markdown reference is missing or escapes package: "
                    f"{path.relative_to(root)} -> {target}"
                )


def validate_evals(root: Path, errors: list[str]) -> None:
    payload = load_json(root / "evals/evals.json", errors, "evals/evals.json")
    if not isinstance(payload, dict):
        errors.append("evals/evals.json must contain an object")
        return
    if payload.get("skill_name") != root.name:
        errors.append("evals/evals.json skill_name must match the package folder")
    cases = payload.get("evals")
    if not isinstance(cases, list) or not cases:
        errors.append("evals/evals.json evals must be a non-empty array")
        return
    ids: set[int] = set()
    for index, value in enumerate(cases, 1):
        if not isinstance(value, dict):
            errors.append(f"Eval {index} must be an object")
            continue
        case_id = value.get("id")
        if isinstance(case_id, bool) or not isinstance(case_id, int) or case_id in ids:
            errors.append(f"Eval {index} id must be a unique integer (booleans are invalid)")
        else:
            ids.add(case_id)
        for field in ("name", "prompt", "expected_output"):
            item = value.get(field)
            if not isinstance(item, str) or not item.strip():
                errors.append(f"Eval {index} {field} must be a non-empty string")
        assertions = value.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            errors.append(f"Eval {index} assertions must be a non-empty array")
        else:
            for assertion_index, assertion in enumerate(assertions, 1):
                if not isinstance(assertion, dict):
                    errors.append(f"Eval {index} assertion {assertion_index} must be an object")
                    continue
                kind = assertion.get("type")
                text = assertion.get("text")
                if not isinstance(kind, str) or kind not in ASSERTION_TYPES:
                    errors.append(f"Eval {index} assertion {assertion_index} has an invalid type")
                if not isinstance(text, str) or not text.strip():
                    errors.append(f"Eval {index} assertion {assertion_index} text must be non-empty")
        files = value.get("files")
        if not isinstance(files, list):
            errors.append(f"Eval {index} files must be an array")
        else:
            for fixture in files:
                if not isinstance(fixture, str) or not fixture.strip():
                    errors.append(f"Eval {index} has an invalid fixture path")
                elif not contained_file(root, root / fixture):
                    errors.append(f"Eval {index} fixture is missing or escapes package: {fixture}")
        tags = value.get("tags")
        if not isinstance(tags, list) or any(
            not isinstance(tag, str) or not tag.strip() for tag in tags
        ):
            errors.append(f"Eval {index} tags must be an array of non-empty strings")


def validate_triggers(root: Path, errors: list[str]) -> None:
    payload = load_json(
        root / "evals/trigger-evals.json", errors, "evals/trigger-evals.json"
    )
    if not isinstance(payload, list) or not payload:
        errors.append("evals/trigger-evals.json must be a non-empty array")
        return
    outcomes: set[bool] = set()
    for index, value in enumerate(payload, 1):
        if not isinstance(value, dict):
            errors.append(f"Trigger {index} must be an object")
            continue
        query = value.get("query")
        outcome = value.get("should_trigger")
        if not isinstance(query, str) or not query.strip():
            errors.append(f"Trigger {index} query must be a non-empty string")
        if not isinstance(outcome, bool):
            errors.append(f"Trigger {index} should_trigger must be boolean")
        else:
            outcomes.add(outcome)
    if outcomes != {False, True}:
        errors.append("Trigger evals must include positive and negative queries")


def validate_skill(skill_path: str | Path) -> ValidationResult:
    root = Path(skill_path).resolve()
    errors: list[str] = []
    if not root.is_dir():
        return ValidationResult((f"Skill path is not a directory: {root}",))
    for relative in REQUIRED_FILES:
        if not contained_file(root, root / relative):
            errors.append(f"Required file is missing or escapes package: {relative}")
    if errors:
        return ValidationResult(tuple(errors))

    skill_text = read_text(root / "SKILL.md", errors, "SKILL.md") if (root / "SKILL.md").is_file() else None
    if skill_text is not None:
        frontmatter = parse_frontmatter(skill_text)
        if frontmatter is None:
            errors.append("SKILL.md must start with closed portable YAML frontmatter")
        else:
            name = frontmatter.get("name")
            description = frontmatter.get("description")
            if name != root.name or name is None or NAME_PATTERN.fullmatch(name) is None:
                errors.append("SKILL.md frontmatter name must be portable and match the folder")
            if not isinstance(description, str) or not description.strip() or len(description) > 1024:
                errors.append("SKILL.md frontmatter description must be 1-1024 characters")

    if (root / "metadata.json").is_file():
        metadata = load_json(root / "metadata.json", errors, "metadata.json")
        if not isinstance(metadata, dict):
            errors.append("metadata.json must contain an object")
        else:
            # Category describes the catalog, not the consumer's install path.
            expected = {"name": root.name, "entrypoint": "SKILL.md", "category": "fun"}
            for key, expected_value in expected.items():
                if metadata.get(key) != expected_value:
                    errors.append(f"metadata.json {key} must equal {expected_value!r}")

    if (root / "evals/evals.json").is_file():
        validate_evals(root, errors)
    if (root / "evals/trigger-evals.json").is_file():
        validate_triggers(root, errors)
    validate_markdown_links(root, errors)
    return ValidationResult(tuple(errors))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {Path(argv[0]).name} <skill-path>", file=sys.stderr)
        return 2
    result = validate_skill(argv[1])
    print(json.dumps(result.as_json(), indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
