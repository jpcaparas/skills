#!/usr/bin/env python3
"""Validate the better-writing package, its routes, and its diagnostic corpus."""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import probe_better_writing
import scan_aiisms


FRONTMATTER_KEY = re.compile(r"[A-Za-z][A-Za-z0-9_-]*\Z")
REFERENCE_NAME = re.compile(r"[a-z][a-z0-9]*(?:[-/][a-z0-9]+)*\Z")
ASSERTION_TYPES = frozenset({"disclosure", "functional", "negative", "structural", "verification"})


@dataclass(frozen=True)
class ValidationState:
    root: Path
    errors: list[str]
    warnings: list[str]
    metrics: dict[str, int]


@dataclass(frozen=True)
class SkillFrontmatter:
    name: str | None
    description: str | None
    version: str | None
    references: tuple[str, ...]
    parse_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class PackageFileStatus:
    contained: bool
    regular_file: bool


def closing_quote_index(value: str, quote: str) -> int | None:
    """Find a YAML-style closing quote, including the two common escape forms."""

    index = 1
    while index < len(value):
        if value[index] != quote:
            index += 1
            continue
        if quote == "'" and index + 1 < len(value) and value[index + 1] == "'":
            index += 2
            continue
        if quote == '"':
            backslashes = 0
            cursor = index - 1
            while cursor >= 1 and value[cursor] == "\\":
                backslashes += 1
                cursor -= 1
            if backslashes % 2 == 1:
                index += 1
                continue
        return index
    return None


def parse_scalar(value: str, line_number: int, errors: list[str]) -> str:
    """Parse the quoted or plain scalars used by this package's frontmatter subset."""

    value = value.strip()
    if value[:1] in {"'", '"'}:
        quote = value[0]
        closing_index = closing_quote_index(value, quote)
        if closing_index is None:
            errors.append(f"Frontmatter line {line_number} has an unterminated quoted scalar")
            return value[1:]
        suffix = value[closing_index + 1 :].strip()
        if suffix and not suffix.startswith("#"):
            errors.append(f"Frontmatter line {line_number} has unexpected text after a quoted scalar")
        parsed = value[1:closing_index]
        return parsed.replace("''", "'") if quote == "'" else parsed
    comment = re.search(r"(?:^|\s)#", value)
    if comment is not None:
        return value[: comment.start()].rstrip()
    return value


def parse_frontmatter(content: str) -> tuple[SkillFrontmatter | None, str]:
    """Parse the package's small YAML subset and retain any structural errors."""

    if re.match(r"\A---\r?\n", content) is None:
        return None, content
    match = re.match(r"\A---\r?\n(?P<header>.*?)\r?\n---(?:\r?\n|\Z)", content, flags=re.DOTALL)
    if match is None:
        malformed = SkillFrontmatter(
            name=None,
            description=None,
            version=None,
            references=(),
            parse_errors=("SKILL.md frontmatter has no closing delimiter",),
        )
        return malformed, content

    fields: dict[str, str] = {}
    metadata: dict[str, str] = {}
    references: list[str] = []
    errors: list[str] = []
    seen_top_level: set[str] = set()
    seen_metadata: set[str] = set()
    section_indents: dict[str, int] = {}
    current_section: str | None = None

    for line_number, raw_line in enumerate(match.group("header").splitlines(), start=2):
        if "\t" in raw_line:
            errors.append(f"Frontmatter line {line_number} contains a tab; use spaces for indentation")
            continue
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent == 0:
            key, separator, raw_value = stripped.partition(":")
            if not separator or FRONTMATTER_KEY.fullmatch(key) is None:
                errors.append(f"Frontmatter line {line_number} is not a valid top-level key")
                current_section = None
                continue
            if key in seen_top_level:
                errors.append(f"Frontmatter line {line_number} duplicates top-level key: {key}")
            else:
                seen_top_level.add(key)
            value = raw_value.strip()
            if key in {"metadata", "references"}:
                if value:
                    errors.append(f"Frontmatter key {key} must be a nested {'mapping' if key == 'metadata' else 'list'}")
                    current_section = None
                else:
                    current_section = key
                continue
            if not value:
                errors.append(f"Frontmatter scalar {key} must have a value")
                current_section = key
                continue
            current_section = None
            parsed_value = parse_scalar(value, line_number, errors)
            if not parsed_value:
                errors.append(f"Frontmatter scalar {key} must have a value")
                continue
            fields.setdefault(key, parsed_value)
            continue
        if current_section not in {"metadata", "references"}:
            section = current_section or "a scalar key"
            errors.append(f"Frontmatter line {line_number} has unexpected nested content under {section}")
            continue
        assert current_section is not None
        expected_indent = section_indents.setdefault(current_section, indent)
        if indent != expected_indent:
            errors.append(
                f"Frontmatter line {line_number} uses inconsistent indentation under {current_section}: "
                f"expected {expected_indent} spaces"
            )
            continue
        if current_section == "metadata":
            key, separator, raw_value = stripped.partition(":")
            value = raw_value.strip()
            if not separator or FRONTMATTER_KEY.fullmatch(key) is None or not value:
                errors.append(f"Frontmatter line {line_number} is not a valid metadata scalar")
                continue
            if key in seen_metadata:
                errors.append(f"Frontmatter line {line_number} duplicates metadata key: {key}")
                continue
            seen_metadata.add(key)
            parsed_value = parse_scalar(value, line_number, errors)
            if not parsed_value:
                errors.append(f"Frontmatter line {line_number} is not a valid metadata scalar")
                continue
            metadata[key] = parsed_value
        elif current_section == "references":
            if not stripped.startswith("- ") or not stripped[2:].strip():
                errors.append(f"Frontmatter line {line_number} is not a valid references list item")
                continue
            reference = parse_scalar(stripped[2:].strip(), line_number, errors)
            if not reference:
                errors.append(f"Frontmatter line {line_number} is not a valid references list item")
                continue
            if REFERENCE_NAME.fullmatch(reference) is None:
                errors.append(f"Frontmatter line {line_number} has an invalid reference name: {reference}")
                continue
            references.append(reference)

    manifest = SkillFrontmatter(
        name=fields.get("name"),
        description=fields.get("description"),
        version=metadata.get("version"),
        references=tuple(references),
        parse_errors=tuple(errors),
    )
    return manifest, content[match.end() :].strip()


def manifest_consistency_errors(
    manifest: SkillFrontmatter,
    metadata_version: str | None,
    available_references: frozenset[str],
) -> list[str]:
    errors: list[str] = []
    if not manifest.version:
        errors.append("SKILL.md frontmatter metadata.version must be a non-empty string")
    if manifest.version and metadata_version and manifest.version != metadata_version:
        errors.append(
            f"Version mismatch: SKILL.md declares {manifest.version}, metadata.json declares {metadata_version}"
        )

    duplicate_references = sorted(
        reference for reference in set(manifest.references) if manifest.references.count(reference) > 1
    )
    if duplicate_references:
        errors.append(f"SKILL.md frontmatter contains duplicate references: {', '.join(duplicate_references)}")

    declared_references = frozenset(manifest.references)
    missing_references = sorted(declared_references - available_references)
    if missing_references:
        errors.append(f"SKILL.md frontmatter declares missing references: {', '.join(missing_references)}")
    undeclared_references = sorted(available_references - declared_references)
    if undeclared_references:
        errors.append(f"Reference files are absent from SKILL.md frontmatter: {', '.join(undeclared_references)}")
    return errors


def run_manifest_self_tests() -> dict[str, bool]:
    sample = """---
name: better-writing
description: "Improve prose."
metadata:
  version: "2.2.0"
references:
  - foundations
  - voice-and-rhythm
---

# Better writing
"""
    manifest, body = parse_frontmatter(sample)
    if manifest is None:
        return {"parses_extended_frontmatter": False}

    def rejects(candidate: str, fragment: str) -> bool:
        parsed, _ = parse_frontmatter(candidate)
        return parsed is not None and any(fragment in error for error in parsed.parse_errors)

    consistent = manifest_consistency_errors(
        manifest,
        "2.2.0",
        frozenset({"foundations", "voice-and-rhythm"}),
    )
    version_mismatch = manifest_consistency_errors(
        manifest,
        "9.9.9",
        frozenset({"foundations", "voice-and-rhythm"}),
    )
    missing_reference = manifest_consistency_errors(
        manifest,
        "2.2.0",
        frozenset({"foundations"}),
    )
    undeclared_reference = manifest_consistency_errors(
        manifest,
        "2.2.0",
        frozenset({"foundations", "voice-and-rhythm", "quality-gates"}),
    )
    duplicate_manifest = SkillFrontmatter(
        name=manifest.name,
        description=manifest.description,
        version=manifest.version,
        references=("foundations", "foundations"),
    )
    duplicate_reference = manifest_consistency_errors(
        duplicate_manifest,
        "2.2.0",
        frozenset({"foundations"}),
    )
    four_space_manifest, _ = parse_frontmatter(
        sample.replace('  version: "2.2.0"', '    version: "2.2.0"')
        .replace("  - foundations", "    - foundations")
        .replace("  - voice-and-rhythm", "    - voice-and-rhythm")
    )
    inline_comment_manifest, _ = parse_frontmatter(
        sample.replace('description: "Improve prose."', 'description: "Improve prose." # note')
    )
    escaped_single_quote_manifest, _ = parse_frontmatter(
        sample.replace('description: "Improve prose."', "description: 'It''s clear.'")
    )
    even_backslash_manifest, _ = parse_frontmatter(
        sample.replace('description: "Improve prose."', 'description: "C:\\\\"')
    )
    return {
        "parses_extended_frontmatter": manifest.name == "better-writing"
        and manifest.description == "Improve prose."
        and manifest.version == "2.2.0"
        and manifest.references == ("foundations", "voice-and-rhythm")
        and body == "# Better writing",
        "accepts_matching_versions_and_references": not consistent,
        "rejects_version_mismatch": any("Version mismatch" in error for error in version_mismatch),
        "rejects_missing_declared_reference": any("declares missing references" in error for error in missing_reference),
        "rejects_undeclared_reference_file": any("absent from SKILL.md frontmatter" in error for error in undeclared_reference),
        "rejects_duplicate_reference": any("duplicate references" in error for error in duplicate_reference),
        "rejects_duplicate_top_level_key": rejects(
            sample.replace("name: better-writing\n", "name: better-writing\nname: duplicate\n"),
            "duplicates top-level key",
        ),
        "rejects_duplicate_metadata_key": rejects(
            sample.replace('  version: "2.2.0"\n', '  version: "2.2.0"\n  version: "2.3.0"\n'),
            "duplicates metadata key",
        ),
        "rejects_scalar_references": rejects(
            sample.replace("references:\n", "references: foundations\n"),
            "must be a nested list",
        ),
        "rejects_malformed_reference_item": rejects(
            sample.replace("  - foundations\n", "  foundations\n"),
            "not a valid references list item",
        ),
        "accepts_consistent_four_space_indentation": four_space_manifest is not None
        and not four_space_manifest.parse_errors
        and four_space_manifest.references == ("foundations", "voice-and-rhythm"),
        "rejects_inconsistent_indentation": rejects(
            sample.replace("  - foundations\n", "    - foundations\n"),
            "inconsistent indentation",
        ),
        "accepts_inline_comment_after_quoted_scalar": inline_comment_manifest is not None
        and not inline_comment_manifest.parse_errors
        and inline_comment_manifest.description == "Improve prose.",
        "accepts_doubled_single_quote_escape": escaped_single_quote_manifest is not None
        and not escaped_single_quote_manifest.parse_errors
        and escaped_single_quote_manifest.description == "It's clear.",
        "accepts_even_backslashes_before_double_quote": even_backslash_manifest is not None
        and not even_backslash_manifest.parse_errors,
        "rejects_comment_only_required_scalar": rejects(
            sample.replace('description: "Improve prose."', "description: # note"),
            "must have a value",
        ),
        "rejects_unclosed_frontmatter": rejects(
            "---\nname: better-writing\ndescription: Improve prose.\n",
            "no closing delimiter",
        ),
    }


def extract_file_references(content: str) -> list[str]:
    """Find packaging references while ignoring code samples and placeholders."""

    refs: set[str] = set()
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder = re.compile(r"[{}<>]|/X\.md$|\s")
    patterns = (
        r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`",
        r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)",
    )
    for expression in patterns:
        for match in re.finditer(expression, stripped):
            candidate = match.group(1)
            if not placeholder.search(candidate):
                refs.add(candidate)
    return sorted(refs)


def syntax_error(path: Path) -> str | None:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return str(exc)
    return None


def inspect_package_file(root: Path, relative: str) -> PackageFileStatus:
    """Resolve a package path without allowing files or symlinks to escape the skill root."""

    resolved_root = root.resolve()
    relative_path = Path(relative)
    if relative_path.is_absolute():
        return PackageFileStatus(contained=False, regular_file=False)
    candidate = (resolved_root / relative_path).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError:
        return PackageFileStatus(contained=False, regular_file=False)
    return PackageFileStatus(contained=True, regular_file=candidate.is_file())


def run_package_path_self_tests(root: Path) -> dict[str, bool]:
    """Cover regular files, directory impostors, and parent traversal."""

    skill_file = inspect_package_file(root, "SKILL.md")
    directory = inspect_package_file(root, "references")
    traversal = inspect_package_file(root, "../SKILL.md")
    absolute = inspect_package_file(root, str(root.resolve() / "SKILL.md"))
    return {
        "accepts_contained_regular_file": skill_file.contained and skill_file.regular_file,
        "rejects_directory_as_file": directory.contained and not directory.regular_file,
        "rejects_parent_traversal": not traversal.contained and not traversal.regular_file,
        "rejects_absolute_package_path": not absolute.contained and not absolute.regular_file,
    }


def is_valid_assertion_type(value: object) -> bool:
    """Accept only the documented string assertion types."""

    return isinstance(value, str) and value in ASSERTION_TYPES


def run_eval_schema_self_tests() -> dict[str, bool]:
    """Cover assertion-type values that previously caused permissive or crashing validation."""

    return {
        "accepts_documented_assertion_type": is_valid_assertion_type("functional"),
        "rejects_unknown_assertion_type": not is_valid_assertion_type("subjective"),
        "rejects_list_assertion_type": not is_valid_assertion_type([]),
        "rejects_object_assertion_type": not is_valid_assertion_type({}),
    }


def validate_evals(path: Path, state: ValidationState) -> None:
    """Validate the portable eval schema rather than merely parsing its JSON."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        state.errors.append(f"evals/evals.json is not valid JSON: {exc}")
        return
    if not isinstance(payload, dict):
        state.errors.append("evals/evals.json must contain an object")
        return
    skill_name = payload.get("skill_name")
    if not isinstance(skill_name, str) or not skill_name.strip():
        state.errors.append("evals/evals.json must contain a non-empty string skill_name")
    elif skill_name != state.root.name:
        state.errors.append("evals/evals.json skill_name must match the skill directory name")
    evals = payload.get("evals")
    if not isinstance(evals, list) or not evals:
        state.errors.append("evals/evals.json must contain a non-empty evals list")
        return
    tags: set[str] = set()
    seen_ids: dict[int, int] = {}
    seen_names: dict[str, int] = {}
    eval_route_checks = 0
    for index, item in enumerate(evals):
        location = f"evals[{index}]"
        if not isinstance(item, dict):
            state.errors.append(f"{location} must be an object")
            continue
        for key in ("id", "name", "prompt", "expected_output", "assertions", "tags"):
            if key not in item:
                state.errors.append(f"{location} is missing {key}")
        eval_id = item.get("id")
        if not isinstance(eval_id, int) or isinstance(eval_id, bool) or eval_id <= 0:
            state.errors.append(f"{location}.id must be a positive integer")
        elif eval_id in seen_ids:
            state.errors.append(f"{location}.id duplicates evals[{seen_ids[eval_id]}].id: {eval_id}")
        else:
            seen_ids[eval_id] = index
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            state.errors.append(f"{location}.name must be a non-empty string")
        elif name in seen_names:
            state.errors.append(f"{location}.name duplicates evals[{seen_names[name]}].name: {name}")
        else:
            seen_names[name] = index
        if not isinstance(item.get("prompt"), str) or not item["prompt"].strip():
            state.errors.append(f"{location}.prompt must be a non-empty string")
        if not isinstance(item.get("expected_output"), str) or not item["expected_output"].strip():
            state.errors.append(f"{location}.expected_output must be a non-empty string")
        assertions = item.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            state.errors.append(f"{location} assertions must be a non-empty list")
        else:
            for assertion_index, assertion in enumerate(assertions):
                assertion_location = f"{location}.assertions[{assertion_index}]"
                if not isinstance(assertion, dict):
                    state.errors.append(f"{assertion_location} must be an object")
                    continue
                text = assertion.get("text")
                if not isinstance(text, str) or not text.strip():
                    state.errors.append(f"{assertion_location}.text must be a non-empty string")
                assertion_type = assertion.get("type")
                if not is_valid_assertion_type(assertion_type):
                    allowed = ", ".join(sorted(ASSERTION_TYPES))
                    state.errors.append(f"{assertion_location}.type must be one of: {allowed}")
        item_tags = item.get("tags")
        if not isinstance(item_tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in item_tags):
            state.errors.append(f"{location} tags must be a list of non-empty strings")
        else:
            tags.update(item_tags)
            prompt = item.get("prompt")
            if isinstance(prompt, str) and prompt.strip():
                should_route = "negative" not in item_tags
                did_route = bool(probe_better_writing.route_prompt(prompt))
                eval_route_checks += 1
                if did_route != should_route:
                    expectation = "route to better-writing" if should_route else "remain outside better-writing"
                    state.errors.append(f"{location}.prompt should {expectation}")
        files = item.get("files", [])
        if not isinstance(files, list) or not all(isinstance(file, str) and file.strip() for file in files):
            state.errors.append(f"{location} files must be a list of non-empty strings when present")
        else:
            for file in files:
                status = inspect_package_file(state.root, file)
                if not status.contained:
                    state.errors.append(f"{location} file escapes the skill package: {file}")
                elif not status.regular_file:
                    state.errors.append(f"{location} references missing regular file: {file}")
    for tag in ("smoke", "edge", "negative", "disclosure", "punctuation-transformation", "digestibility"):
        if tag not in tags:
            state.errors.append(f"Missing eval coverage for tag: {tag}")
    state.metrics["eval_count"] = len(evals)
    state.metrics["eval_route_checks"] = eval_route_checks


def validate_trigger_evals(path: Path, state: ValidationState) -> None:
    """Validate invocation examples and require both positive and negative coverage."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        state.errors.append(f"evals/trigger-evals.json is not valid JSON: {exc}")
        return
    if not isinstance(payload, list) or not payload:
        state.errors.append("evals/trigger-evals.json must contain a non-empty list")
        return
    seen_queries: set[str] = set()
    polarities: set[bool] = set()
    trigger_route_checks = 0
    for index, item in enumerate(payload):
        location = f"trigger-evals[{index}]"
        if not isinstance(item, dict):
            state.errors.append(f"{location} must be an object")
            continue
        query = item.get("query")
        should_trigger = item.get("should_trigger")
        if not isinstance(query, str) or not query.strip():
            state.errors.append(f"{location}.query must be a non-empty string")
        elif query in seen_queries:
            state.errors.append(f"{location}.query duplicates an earlier trigger eval")
        else:
            seen_queries.add(query)
        if not isinstance(should_trigger, bool):
            state.errors.append(f"{location}.should_trigger must be a boolean")
        else:
            polarities.add(should_trigger)
            if isinstance(query, str) and query.strip():
                did_trigger = bool(probe_better_writing.route_prompt(query))
                trigger_route_checks += 1
                if did_trigger != should_trigger:
                    state.errors.append(
                        f"{location}.query routes as {did_trigger} but should_trigger is {should_trigger}"
                    )
    if polarities != {False, True}:
        state.errors.append("Trigger evals must include positive and negative cases")
    state.metrics["trigger_eval_count"] = len(payload)
    state.metrics["trigger_route_checks"] = trigger_route_checks


def validate_routes(state: ValidationState) -> None:
    """Ensure routing tests assert both positive and excluded near-miss paths."""

    suite = probe_better_writing.run_suite()
    checks = suite.get("checks")
    if not isinstance(checks, list):
        state.errors.append("Probe suite returned an invalid checks payload")
        return
    for check in checks:
        if not isinstance(check, dict):
            state.errors.append("Probe suite returned a non-object check")
            continue
        if not check.get("passed"):
            state.errors.append(f"Probe route failed: {check.get('name', 'unknown')}")
        for reference in check.get("expected", []):
            if not isinstance(reference, str) or not (state.root / reference).is_file():
                state.errors.append(f"Probe requires missing reference: {reference}")
        for reference in check.get("forbidden", []):
            if not isinstance(reference, str):
                state.errors.append(f"Probe has invalid forbidden reference in {check.get('name', 'unknown')}")
    state.metrics["route_checks"] = len(checks)


def validate_scanner(state: ValidationState) -> None:
    """Schema-load the corpus, compile all regexes, and run scanner safety checks."""

    corpus_path = state.root / "assets" / "aiisms.json"
    try:
        patterns = scan_aiisms.load_corpus(corpus_path)
    except scan_aiisms.CorpusError as exc:
        state.errors.append(f"Diagnostic corpus invalid: {exc}")
        return
    state.metrics["aiism_patterns"] = len(patterns)
    self_test = scan_aiisms.run_self_tests()
    checks = self_test.get("checks", {})
    if not self_test.get("passed"):
        failures = [name for name, passed in checks.items() if not passed] if isinstance(checks, dict) else ["unknown"]
        state.errors.append(f"Scanner self-test failed: {', '.join(failures)}")


def validate_manifest_parser(state: ValidationState) -> None:
    """Exercise extended-frontmatter parsing and package-consistency failure paths."""

    checks = run_manifest_self_tests()
    state.metrics["manifest_checks"] = len(checks)
    state.metrics["manifest_checks_passed"] = sum(1 for passed in checks.values() if passed)
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        state.errors.append(f"Manifest self-test failed: {', '.join(failures)}")


def validate_eval_schema(state: ValidationState) -> None:
    """Exercise eval assertion types, including unhashable JSON values."""

    checks = run_eval_schema_self_tests()
    state.metrics["eval_schema_checks"] = len(checks)
    state.metrics["eval_schema_checks_passed"] = sum(1 for passed in checks.values() if passed)
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        state.errors.append(f"Eval schema self-test failed: {', '.join(failures)}")


def validate_package_paths(state: ValidationState) -> None:
    """Exercise package containment before validating declared local files."""

    checks = run_package_path_self_tests(state.root)
    state.metrics["package_path_checks"] = len(checks)
    state.metrics["package_path_checks_passed"] = sum(1 for passed in checks.values() if passed)
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        state.errors.append(f"Package path self-test failed: {', '.join(failures)}")


def validate_skill(skill_path: str) -> dict[str, object]:
    root = Path(skill_path).resolve()
    state = ValidationState(
        root=root,
        errors=[],
        warnings=[],
        metrics={
            "skill_md_lines": 0,
            "reference_count": 0,
            "total_lines": 0,
            "manifest_checks": 0,
            "manifest_checks_passed": 0,
            "eval_schema_checks": 0,
            "eval_schema_checks_passed": 0,
            "eval_route_checks": 0,
            "trigger_route_checks": 0,
            "package_path_checks": 0,
            "package_path_checks_passed": 0,
        },
    )
    validate_manifest_parser(state)
    validate_eval_schema(state)
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        return {"valid": False, "errors": ["SKILL.md does not exist"], "warnings": [], "metrics": state.metrics}
    validate_package_paths(state)
    content = skill_md.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    state.metrics["skill_md_lines"] = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    state.metrics["total_lines"] = state.metrics["skill_md_lines"]
    if frontmatter is None:
        state.errors.append("SKILL.md has no YAML frontmatter")
    else:
        state.errors.extend(frontmatter.parse_errors)
        if not frontmatter.parse_errors:
            if frontmatter.name != root.name:
                state.errors.append("Frontmatter name does not match directory name")
            if not frontmatter.description:
                state.errors.append("Frontmatter missing description")
    if body.count("\n") + 1 > 500:
        state.warnings.append("SKILL.md body exceeds 500 lines target")
    for directory in ("references", "scripts", "templates", "evals", "assets", "agents"):
        if not (root / directory).is_dir():
            state.errors.append(f"Missing directory: {directory}/")
    required_files = (
        "README.md", "AGENTS.md", "metadata.json", "agents/openai.yaml",
        "scripts/probe_better_writing.py", "scripts/scan_aiisms.py", "scripts/validate.py", "scripts/test_skill.py",
        "assets/aiisms.json", "evals/evals.json", "evals/trigger-evals.json",
    )
    for relative in required_files:
        if not (root / relative).is_file():
            state.errors.append(f"Missing required file: {relative}")
    for relative in extract_file_references(content):
        status = inspect_package_file(root, relative)
        if not status.contained:
            state.errors.append(f"Referenced file escapes the skill package: {relative}")
        elif not status.regular_file:
            state.errors.append(f"Referenced regular file does not exist: {relative}")
    for relative in ("scripts/probe_better_writing.py", "scripts/scan_aiisms.py", "scripts/validate.py", "scripts/test_skill.py"):
        path = root / relative
        if path.is_file() and (error := syntax_error(path)):
            state.errors.append(f"Python syntax error in {relative}: {error}")
    metadata = root / "metadata.json"
    metadata_version: str | None = None
    if metadata.is_file():
        try:
            metadata_payload: object = json.loads(metadata.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            state.errors.append(f"metadata.json is not valid JSON: {exc}")
        else:
            if not isinstance(metadata_payload, dict):
                state.errors.append("metadata.json must contain an object")
            else:
                raw_version = metadata_payload.get("version")
                if isinstance(raw_version, str) and raw_version:
                    metadata_version = raw_version
                else:
                    state.errors.append("metadata.json version must be a non-empty string")
    references = root / "references"
    available_references: frozenset[str] = frozenset()
    if references.is_dir():
        reference_paths = sorted(references.rglob("*.md"))
        available_references = frozenset(
            reference.relative_to(references).with_suffix("").as_posix() for reference in reference_paths
        )
        for reference in reference_paths:
            reference_content = reference.read_text(encoding="utf-8")
            lines = reference_content.count("\n") + (1 if reference_content and not reference_content.endswith("\n") else 0)
            state.metrics["reference_count"] += 1
            state.metrics["total_lines"] += lines
            if lines > 1000:
                state.errors.append(f"Reference file exceeds 1000 lines: {reference.relative_to(root)}")
            for relative in extract_file_references(reference_content):
                status = inspect_package_file(root, relative)
                if not status.contained:
                    state.errors.append(f"Referenced file escapes the skill package: {relative}")
                elif not status.regular_file:
                    state.errors.append(f"Referenced regular file does not exist: {relative}")
    if frontmatter is not None and not frontmatter.parse_errors:
        state.errors.extend(manifest_consistency_errors(frontmatter, metadata_version, available_references))
    evals_path = root / "evals" / "evals.json"
    if evals_path.is_file():
        validate_evals(evals_path, state)
    trigger_evals_path = root / "evals" / "trigger-evals.json"
    if trigger_evals_path.is_file():
        validate_trigger_evals(trigger_evals_path, state)
    validate_routes(state)
    validate_scanner(state)
    return {"valid": not state.errors, "errors": state.errors, "warnings": state.warnings, "metrics": state.metrics}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        return 1
    result = validate_skill(sys.argv[1])
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
