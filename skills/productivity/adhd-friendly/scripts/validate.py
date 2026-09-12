#!/usr/bin/env python3
"""Validate the portable adhd-friendly skill package."""

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
    "THIRD_PARTY_NOTICES.md",
    "references/research-notes.md",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "skill-card.prompt.md",
    "skill-card.png",
}
REQUIRED_HEADINGS = {
    "## Invocation boundary",
    "## Operating contract",
    "## Route the request",
    "## Shared defaults",
    "## Safety and clinical boundaries",
    "## Evidence and attribution",
    "## Pre-send gate",
}
REQUIRED_EVAL_TAGS = {
    "smoke",
    "edge",
    "negative",
    "disclosure",
    "safety",
    "autonomy",
    "re-entry",
}
ASSERTION_TYPES = {
    "functional",
    "structural",
    "disclosure",
    "negative",
    "verification",
}
UPSTREAM_URL = "https://github.com/ayghri/i-have-adhd"
UPSTREAM_COMMIT = "72c33eee81ea439cf01991e93729adfce2ffc99e"
UPSTREAM_COPYRIGHT = "Copyright (c) 2026 Ayoub Ghriss"
MACHINE_PATH_PATTERNS = (
    re.compile(r"/Users/"),
    re.compile(r"/home/"),
    re.compile(r"[A-Za-z]:\\\\"),
)
UPSTREAM_OVERGENERALIZATIONS = (
    "Dopamine is scarce",
    "The reader has ADHD",
    "Trigger even on casual",
    "whenever responding to ANY user message",
    "Time estimates feel uniform",
)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Stable result contract consumed by local tests and repository tooling."""

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


def line_count(path: Path) -> int:
    """Count logical text lines without requiring a trailing newline."""

    text = path.read_text(encoding="utf-8")
    return len(text.splitlines())


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the flat portable fields governed by this package."""

    match = re.match(r"^---\n(?P<body>.*?)\n---\n", text, re.DOTALL)
    if match is None:
        return {}

    result: dict[str, str] = {}
    for line in match.group("body").splitlines():
        field = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$", line)
        if field is None:
            continue
        result[field.group(1)] = field.group(2).strip().strip("\"'")
    return result


def load_json(path: Path) -> object:
    """Parse JSON at the filesystem boundary; callers narrow the result."""

    return json.loads(path.read_text(encoding="utf-8"))


def as_object(value: object) -> dict[str, object] | None:
    """Narrow an unknown JSON value to an object with string keys."""

    if not isinstance(value, dict):
        return None
    if not all(isinstance(key, str) for key in value):
        return None
    return {str(key): item for key, item in value.items()}


def as_object_list(value: object) -> list[dict[str, object]] | None:
    """Narrow an unknown JSON value to a list of objects."""

    if not isinstance(value, list):
        return None
    objects: list[dict[str, object]] = []
    for item in value:
        narrowed = as_object(item)
        if narrowed is None:
            return None
        objects.append(narrowed)
    return objects


def as_string_list(value: object) -> list[str] | None:
    """Narrow an unknown JSON value to a list of strings."""

    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return [item for item in value if isinstance(item, str)]


def extract_package_references(text: str) -> list[str]:
    """Find literal relative package paths outside fenced examples."""

    without_code_fences = re.sub(r"```[\s\S]*?```", "", text)
    matches = re.findall(
        r"`((?:references|scripts|evals|assets|agents)/[^`\s]+|THIRD_PARTY_NOTICES\.md)`",
        without_code_fences,
    )
    return sorted(set(matches))


def has_machine_specific_path(text: str) -> bool:
    return any(pattern.search(text) is not None for pattern in MACHINE_PATH_PATTERNS)


def validate_portable_core(root: Path, errors: list[str], warnings: list[str]) -> None:
    skill_path = root / "SKILL.md"
    if not skill_path.is_file():
        errors.append("missing required file: SKILL.md")
        return

    text = skill_path.read_text(encoding="utf-8")
    frontmatter = parse_frontmatter(text)

    if frontmatter.get("name") != root.name:
        errors.append("frontmatter name must match the skill directory")
    description = frontmatter.get("description", "")
    if not description:
        errors.append("frontmatter description is required")
    elif len(description) > 1024:
        errors.append("frontmatter description exceeds the Agent Skills limit")
    if frontmatter.get("license") != "MIT; see THIRD_PARTY_NOTICES.md":
        errors.append("frontmatter license must point to THIRD_PARTY_NOTICES.md")

    if line_count(skill_path) > 500:
        errors.append("SKILL.md exceeds the 500-line portability ceiling")
    if has_machine_specific_path(text):
        errors.append("SKILL.md contains a machine-specific path")

    for heading in sorted(REQUIRED_HEADINGS):
        if heading not in text:
            errors.append(f"SKILL.md missing required contract: {heading}")

    for phrase in UPSTREAM_OVERGENERALIZATIONS:
        if phrase.casefold() in text.casefold():
            errors.append(f"SKILL.md reintroduces an upstream overgeneralization: {phrase}")

    if "TODO" in text or "{{" in text:
        errors.append("SKILL.md contains an unresolved placeholder")

    wrappers = (root / "README.md", root / "AGENTS.md")
    for wrapper in wrappers:
        if not wrapper.is_file():
            continue
        if has_machine_specific_path(wrapper.read_text(encoding="utf-8")):
            errors.append(f"{wrapper.name} contains a machine-specific path")
    if (root / "README.md").is_file() and line_count(root / "README.md") > 80:
        warnings.append("README.md is no longer a thin packaging wrapper")
    if (root / "AGENTS.md").is_file() and line_count(root / "AGENTS.md") > 40:
        warnings.append("AGENTS.md is no longer a thin packaging wrapper")


def validate_attribution(root: Path, errors: list[str]) -> None:
    metadata_path = root / "metadata.json"
    notice_path = root / "THIRD_PARTY_NOTICES.md"
    if not metadata_path.is_file() or not notice_path.is_file():
        return

    try:
        payload = as_object(load_json(metadata_path))
    except json.JSONDecodeError as exc:
        errors.append(f"metadata.json is invalid JSON: {exc}")
        return
    if payload is None:
        errors.append("metadata.json must contain a JSON object")
        return

    if payload.get("license") != "MIT":
        errors.append("metadata.json must declare the skill license as MIT")
    attributions = as_object_list(payload.get("attribution"))
    if attributions is None or len(attributions) != 1:
        errors.append("metadata.json must contain one structured attribution entry")
        return

    attribution = attributions[0]
    expected: dict[str, str] = {
        "title": "i-have-adhd",
        "creator": "Ayoub Ghriss",
        "source_url": UPSTREAM_URL,
        "source_commit": UPSTREAM_COMMIT,
        "source_license": "MIT",
        "copyright": UPSTREAM_COPYRIGHT,
        "notice": "THIRD_PARTY_NOTICES.md",
    }
    for field, value in expected.items():
        if attribution.get(field) != value:
            errors.append(f"metadata attribution field {field!r} must equal {value!r}")
    adaptation = attribution.get("adaptation")
    if not isinstance(adaptation, str) or not adaptation.strip():
        errors.append("metadata attribution must describe the adaptation")

    references = as_string_list(payload.get("references"))
    if references is None or UPSTREAM_URL + "/tree/" + UPSTREAM_COMMIT not in references:
        errors.append("metadata references must include the inspected upstream revision")

    notice = notice_path.read_text(encoding="utf-8")
    required_notice_fragments = (
        UPSTREAM_URL,
        UPSTREAM_COMMIT,
        "MIT License",
        UPSTREAM_COPYRIGHT,
        "Permission is hereby granted, free of charge",
        "THE SOFTWARE IS PROVIDED \"AS IS\"",
    )
    for fragment in required_notice_fragments:
        if fragment not in notice:
            errors.append(f"THIRD_PARTY_NOTICES.md missing required MIT fragment: {fragment}")


def validate_behavioral_evals(root: Path, errors: list[str], metrics: dict[str, int]) -> None:
    evals_path = root / "evals" / "evals.json"
    if not evals_path.is_file():
        return

    try:
        payload = as_object(load_json(evals_path))
    except json.JSONDecodeError as exc:
        errors.append(f"evals/evals.json is invalid JSON: {exc}")
        return
    if payload is None:
        errors.append("evals/evals.json must contain a JSON object")
        return
    if payload.get("skill_name") != root.name:
        errors.append("eval skill_name must match the skill directory")
    if payload.get("created_by") != "skill-creator-advanced":
        errors.append("evals must record skill-creator-advanced as created_by")

    cases = as_object_list(payload.get("evals"))
    if cases is None or not cases:
        errors.append("evals/evals.json must contain behavioral cases")
        return

    metrics["behavioral_evals"] = len(cases)
    seen_ids: set[int] = set()
    seen_tags: set[str] = set()

    for index, case in enumerate(cases, start=1):
        label = case.get("name", f"case-{index}")
        case_id = case.get("id")
        if type(case_id) is not int:
            errors.append(f"eval {label!r} must have an integer id")
        elif case_id in seen_ids:
            errors.append(f"eval id {case_id} is duplicated")
        else:
            seen_ids.add(case_id)

        for field in ("name", "prompt", "expected_output"):
            value = case.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"eval {label!r} missing non-empty field: {field}")

        assertions = as_object_list(case.get("assertions"))
        if assertions is None or not assertions:
            errors.append(f"eval {label!r} must have typed assertions")
        else:
            for assertion in assertions:
                text = assertion.get("text")
                assertion_type = assertion.get("type")
                if not isinstance(text, str) or not text.strip():
                    errors.append(f"eval {label!r} has an empty assertion")
                if assertion_type not in ASSERTION_TYPES:
                    errors.append(f"eval {label!r} has invalid assertion type: {assertion_type!r}")

        tags = as_string_list(case.get("tags"))
        if tags is None:
            errors.append(f"eval {label!r} tags must be strings")
        else:
            seen_tags.update(tags)

        files = as_string_list(case.get("files", []))
        if files is None:
            errors.append(f"eval {label!r} files must be strings")
            continue
        for relative in files:
            candidate = (root / relative).resolve()
            if not candidate.is_relative_to(root):
                errors.append(f"eval {label!r} file escapes the package: {relative}")
            elif not candidate.is_file():
                errors.append(f"eval {label!r} references a missing file: {relative}")

    missing_tags = sorted(REQUIRED_EVAL_TAGS - seen_tags)
    if missing_tags:
        errors.append("missing behavioral eval coverage tags: " + ", ".join(missing_tags))


def validate_trigger_evals(root: Path, errors: list[str], metrics: dict[str, int]) -> None:
    trigger_path = root / "evals" / "trigger-evals.json"
    if not trigger_path.is_file():
        return

    try:
        cases = as_object_list(load_json(trigger_path))
    except json.JSONDecodeError as exc:
        errors.append(f"evals/trigger-evals.json is invalid JSON: {exc}")
        return
    if cases is None or not cases:
        errors.append("trigger evals must contain a JSON array of cases")
        return

    positives = 0
    negatives = 0
    queries: set[str] = set()
    for case in cases:
        query = case.get("query")
        should_trigger = case.get("should_trigger")
        if not isinstance(query, str) or not query.strip():
            errors.append("trigger eval query must be a non-empty string")
        elif query in queries:
            errors.append(f"duplicate trigger eval query: {query}")
        else:
            queries.add(query)
        if type(should_trigger) is not bool:
            errors.append(f"trigger eval {query!r} must use a boolean should_trigger")
        elif should_trigger:
            positives += 1
        else:
            negatives += 1

    metrics["trigger_evals"] = len(cases)
    if positives < 4 or negatives < 4:
        errors.append("trigger evals require at least four positive and four negative cases")


def validate_references_and_scripts(root: Path, errors: list[str], metrics: dict[str, int]) -> None:
    markdown_paths = sorted(root.glob("*.md")) + sorted((root / "references").rglob("*.md"))
    reference_checks = 0
    for path in markdown_paths:
        text = path.read_text(encoding="utf-8")
        if path.parent.name == "references" and line_count(path) > 1000:
            errors.append(f"reference exceeds 1000 lines: {path.relative_to(root)}")
        if has_machine_specific_path(text):
            errors.append(f"portable prose contains a machine-specific path: {path.relative_to(root)}")
        for relative in extract_package_references(text):
            reference_checks += 1
            candidate = (root / relative).resolve()
            if not candidate.is_relative_to(root):
                errors.append(f"reference escapes the package: {relative}")
            elif not candidate.exists():
                errors.append(f"missing referenced package file: {relative}")
    metrics["cross_references"] = reference_checks

    for path in sorted(root.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            errors.append(f"python syntax error in {path.relative_to(root)}: {exc}")


def validate_skill(skill_path: str | Path) -> ValidationResult:
    """Validate every governed surface of one adhd-friendly package."""

    root = Path(skill_path).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {
        "skill_lines": line_count(root / "SKILL.md") if (root / "SKILL.md").is_file() else 0,
        "behavioral_evals": 0,
        "trigger_evals": 0,
        "cross_references": 0,
    }

    for relative in sorted(REQUIRED_FILES):
        if not (root / relative).is_file():
            errors.append(f"missing required file: {relative}")

    validate_portable_core(root, errors, warnings)
    validate_attribution(root, errors)
    validate_behavioral_evals(root, errors, metrics)
    validate_trigger_evals(root, errors, metrics)
    validate_references_and_scripts(root, errors, metrics)

    return ValidationResult(
        valid=not errors,
        errors=errors,
        warnings=warnings,
        metrics=metrics,
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate.py <skill-path>", file=sys.stderr)
        return 2

    result = validate_skill(sys.argv[1])
    print(json.dumps(result.to_json_object(), indent=2))
    return 0 if result.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
