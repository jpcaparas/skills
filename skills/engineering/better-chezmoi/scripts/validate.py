#!/usr/bin/env python3
"""Validate the better-chezmoi package, routes, evals, and docs corpus."""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence, cast


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import official_docs  # noqa: E402 - sibling import after direct-execution path bootstrap


REQUIRED_EVAL_TAGS = {"smoke", "edge", "negative", "disclosure"}
ALLOWED_ASSERTION_TYPES = {
    "disclosure",
    "functional",
    "negative",
    "structural",
    "verification",
}


@dataclass(slots=True)
class ValidationState:
    root: Path
    errors: list[str]
    warnings: list[str]
    metrics: dict[str, int]


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    match = re.match(
        r"\A---\s*\n(?P<header>.*?)\n---\s*\n(?P<body>.*)\Z", content, re.DOTALL
    )
    if match is None:
        return None, content
    data: dict[str, str] = {}
    for line in match.group("header").splitlines():
        field = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if field is None:
            continue
        value = field.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        data[field.group(1)] = value
    return data, match.group("body")


def require_mapping(
    value: object, context: str, state: ValidationState
) -> Mapping[str, object] | None:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        state.errors.append(f"{context} must be an object with string keys")
        return None
    return cast(Mapping[str, object], value)


def extract_local_references(content: str) -> tuple[str, ...]:
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    found: set[str] = set()
    patterns = (
        r"`((?:references|scripts|evals|agents|assets|templates)/[^`\s]+)`",
        r"\[[^\]]*\]\(((?:references|scripts|evals|agents|assets|templates)/[^)\s]+)\)",
    )
    for pattern in patterns:
        found.update(re.findall(pattern, stripped))
    return tuple(sorted(found))


def validate_python(path: Path, state: ValidationState) -> None:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        state.errors.append(
            f"Python syntax error in {path.relative_to(state.root)}: {exc}"
        )


def validate_evals(path: Path, state: ValidationState) -> None:
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        state.errors.append(f"evals/evals.json is invalid JSON: {exc}")
        return
    root = require_mapping(raw, "evals", state)
    if root is None:
        return
    if root.get("skill_name") != state.root.name:
        state.errors.append("evals.skill_name must match the skill directory")
    cases = root.get("evals")
    if not isinstance(cases, list) or not cases:
        state.errors.append("evals.evals must be a non-empty array")
        return
    ids: set[int] = set()
    names: set[str] = set()
    tags: set[str] = set()
    assertions_checked = 0
    for index, raw_case in enumerate(cases):
        context = f"evals.evals[{index}]"
        case = require_mapping(raw_case, context, state)
        if case is None:
            continue
        case_id = case.get("id")
        if not isinstance(case_id, int) or isinstance(case_id, bool) or case_id < 1:
            state.errors.append(f"{context}.id must be a positive integer")
        elif case_id in ids:
            state.errors.append(f"Duplicate eval id: {case_id}")
        else:
            ids.add(case_id)
        name = case.get("name")
        if not isinstance(name, str) or not name:
            state.errors.append(f"{context}.name must be a non-empty string")
        elif name in names:
            state.errors.append(f"Duplicate eval name: {name}")
        else:
            names.add(name)
        for field in ("prompt", "expected_output"):
            if not isinstance(case.get(field), str) or not str(case[field]).strip():
                state.errors.append(f"{context}.{field} must be a non-empty string")
        raw_assertions = case.get("assertions")
        if not isinstance(raw_assertions, list) or not raw_assertions:
            state.errors.append(f"{context}.assertions must be a non-empty array")
        else:
            for assertion_index, raw_assertion in enumerate(raw_assertions):
                assertion_context = f"{context}.assertions[{assertion_index}]"
                assertion = require_mapping(raw_assertion, assertion_context, state)
                if assertion is None:
                    continue
                if (
                    not isinstance(assertion.get("text"), str)
                    or not str(assertion["text"]).strip()
                ):
                    state.errors.append(f"{assertion_context}.text must be non-empty")
                assertion_type = assertion.get("type")
                if assertion_type not in ALLOWED_ASSERTION_TYPES:
                    state.errors.append(
                        f"{assertion_context}.type is unsupported: {assertion_type}"
                    )
                assertions_checked += 1
        raw_tags = case.get("tags")
        if (
            not isinstance(raw_tags, list)
            or not raw_tags
            or not all(isinstance(tag, str) and tag for tag in raw_tags)
        ):
            state.errors.append(f"{context}.tags must be a non-empty string array")
        else:
            tags.update(cast(list[str], raw_tags))
        raw_files = case.get("files", [])
        if not isinstance(raw_files, list) or not all(
            isinstance(item, str) and item for item in raw_files
        ):
            state.errors.append(f"{context}.files must be a string array when present")
        else:
            for item in cast(list[str], raw_files):
                resolved = (state.root / item).resolve()
                if state.root not in resolved.parents or not resolved.is_file():
                    state.errors.append(
                        f"{context} references missing or unsafe fixture: {item}"
                    )
    missing_tags = sorted(REQUIRED_EVAL_TAGS - tags)
    if missing_tags:
        state.errors.append("Missing eval coverage: " + ", ".join(missing_tags))
    state.metrics["eval_count"] = len(cases)
    state.metrics["eval_assertions"] = assertions_checked


def validate_triggers(path: Path, state: ValidationState) -> None:
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        state.errors.append(f"trigger-evals.json is invalid JSON: {exc}")
        return
    if not isinstance(raw, list) or not raw:
        state.errors.append("trigger-evals.json must be a non-empty array")
        return
    positive = 0
    negative = 0
    queries: set[str] = set()
    for index, raw_case in enumerate(raw):
        case = require_mapping(raw_case, f"trigger-evals[{index}]", state)
        if case is None:
            continue
        query = case.get("query")
        expected = case.get("should_trigger")
        if not isinstance(query, str) or not query.strip():
            state.errors.append(f"trigger-evals[{index}].query must be non-empty")
        elif query in queries:
            state.errors.append(f"Duplicate trigger query: {query}")
        else:
            queries.add(query)
        if not isinstance(expected, bool):
            state.errors.append(
                f"trigger-evals[{index}].should_trigger must be boolean"
            )
        elif expected:
            positive += 1
        else:
            negative += 1
    if positive < 3 or negative < 3:
        state.errors.append(
            "trigger-evals.json needs at least three positive and three negative cases"
        )
    state.metrics["trigger_count"] = len(raw)


def validate_metadata(path: Path, state: ValidationState) -> None:
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        state.errors.append(f"metadata.json is invalid JSON: {exc}")
        return
    metadata = require_mapping(raw, "metadata", state)
    if metadata is None:
        return
    if metadata.get("name") != state.root.name:
        state.errors.append("metadata.name must match the skill directory")
    if not isinstance(metadata.get("version"), str):
        state.errors.append("metadata.version must be a string")


def validate_skill(skill_path: str) -> dict[str, object]:
    root = Path(skill_path).resolve()
    state = ValidationState(
        root=root,
        errors=[],
        warnings=[],
        metrics={"skill_lines": 0, "reference_files": 0, "official_documents": 0},
    )
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        return {
            "valid": False,
            "errors": ["SKILL.md does not exist"],
            "warnings": [],
            "metrics": state.metrics,
        }
    content = skill_md.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    state.metrics["skill_lines"] = len(content.splitlines())
    if frontmatter is None:
        state.errors.append("SKILL.md must have YAML frontmatter")
    else:
        if frontmatter.get("name") != root.name:
            state.errors.append("Frontmatter name must match the skill directory")
        description = frontmatter.get("description", "")
        if not description:
            state.errors.append("Frontmatter description is required")
        elif len(description) > 450:
            state.errors.append(
                f"Frontmatter description exceeds 450 characters: {len(description)}"
            )
    if len(body.splitlines()) > 500:
        state.errors.append("SKILL.md body exceeds 500 lines")
    required_files = (
        "README.md",
        "AGENTS.md",
        "metadata.json",
        "agents/openai.yaml",
        "evals/evals.json",
        "evals/trigger-evals.json",
        "scripts/official_docs.py",
        "scripts/probe_chezmoi.py",
        "scripts/validate.py",
        "scripts/test_skill.py",
        "skill-card.prompt.md",
        "skill-card.png",
    )
    for relative in required_files:
        if not (root / relative).is_file():
            state.errors.append(f"Missing required file: {relative}")
    for relative in extract_local_references(content):
        if not (root / relative).exists():
            state.errors.append(f"SKILL.md references missing path: {relative}")
    for path in sorted((root / "references").rglob("*.md")):
        state.metrics["reference_files"] += 1
        reference = path.read_text(encoding="utf-8")
        if len(reference.splitlines()) > 1000:
            state.errors.append(
                f"Reference exceeds 1000 lines: {path.relative_to(root)}"
            )
        for relative in extract_local_references(reference):
            if not (root / relative).exists():
                state.errors.append(
                    f"{path.relative_to(root)} references missing path: {relative}"
                )
    for path in sorted((root / "scripts").glob("*.py")):
        validate_python(path, state)
    placeholders = re.findall(r"\b(?:TODO|TBD|PLACEHOLDER)\b", content, re.IGNORECASE)
    if placeholders:
        state.errors.append("SKILL.md contains unresolved placeholder text")
    metadata = root / "metadata.json"
    if metadata.is_file():
        validate_metadata(metadata, state)
    evals = root / "evals" / "evals.json"
    if evals.is_file():
        validate_evals(evals, state)
    triggers = root / "evals" / "trigger-evals.json"
    if triggers.is_file():
        validate_triggers(triggers, state)
    ui_manifest = root / "agents" / "openai.yaml"
    if ui_manifest.is_file():
        ui_text = ui_manifest.read_text(encoding="utf-8")
        for required in (
            "interface:",
            "display_name:",
            "short_description:",
            "default_prompt:",
        ):
            if required not in ui_text:
                state.errors.append(f"agents/openai.yaml is missing {required}")
        if "$better-chezmoi" not in ui_text:
            state.errors.append(
                "agents/openai.yaml default_prompt must mention $better-chezmoi"
            )
        short_match = re.search(
            r'^\s*short_description:\s*"([^"]+)"\s*$', ui_text, re.MULTILINE
        )
        if short_match is None or not 25 <= len(short_match.group(1)) <= 64:
            state.errors.append(
                "agents/openai.yaml short_description must be a quoted 25-64 character string"
            )
    corpus = root / "references" / "official-docs"
    try:
        manifest = official_docs.validate_corpus(corpus)
        state.metrics["official_documents"] = len(manifest.documents)
    except official_docs.CorpusError as exc:
        state.errors.append(f"Official docs corpus invalid: {exc}")
    return {
        "valid": not state.errors,
        "errors": state.errors,
        "warnings": state.warnings,
        "metrics": state.metrics,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        return 1
    result = validate_skill(args[0])
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
