#!/usr/bin/env python3
"""Validate the namethatui skill package and its release-critical contracts."""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit


REQUIRED_FILES: tuple[str, ...] = (
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "agents/openai.yaml",
    "references/component-families.md",
    "references/research-and-sources.md",
    "references/visual-intake.md",
    "scripts/prepare_research.py",
    "scripts/check_benchmark_evidence.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "evals/files/modal-with-scrim.png",
    "evals/files/tree-disclosure.png",
    "skill-card.png",
    "skill-card.prompt.md",
)
REQUIRED_EVAL_TAGS: frozenset[str] = frozenset({"smoke", "edge", "negative", "disclosure"})
REQUIRED_SKILL_PHRASES: tuple[str, ...] = (
    "Plain-language description",
    "Screenshot or mockup",
    "Live page or user-supplied URL",
    "DOM, code, or accessibility clues",
    "namethatui.com",
    "agent-browser",
    "Prompt-ready wording",
)
LOCAL_LINK_PATTERN = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
INLINE_PATH_PATTERN = re.compile(
    r"`((?:references|scripts|evals|agents|assets|templates)/[^`\s]+)`"
)


@dataclass(slots=True)
class ValidationReport:
    """Machine-readable validation result."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, int] = field(
        default_factory=lambda: {
            "skill_md_lines": 0,
            "reference_count": 0,
            "eval_count": 0,
            "trigger_eval_count": 0,
            "local_links_checked": 0,
            "python_files_checked": 0,
        }
    )

    def error(self, message: str) -> None:
        self.valid = False
        self.errors.append(message)


def string_keyed_mapping(value: object) -> dict[str, object] | None:
    """Narrow an untrusted JSON object to a string-keyed mapping."""

    if not isinstance(value, dict):
        return None
    result: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        result[key] = item
    return result


def load_json(path: Path, report: ValidationReport) -> object | None:
    """Load one JSON boundary and preserve parse failures as validation errors."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        report.error(f"Cannot read {path.name}: {exc}")
    except json.JSONDecodeError as exc:
        report.error(f"{path.name} is not valid JSON: {exc}")
    return None


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    """Parse the portable top-level scalar fields used by this package."""

    if not content.startswith("---\n"):
        return None, content
    end = content.find("\n---\n", 4)
    if end == -1:
        return None, content

    values: dict[str, str] = {}
    for line in content[4:end].splitlines():
        if not line or line[0].isspace() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)", line)
        if match is None:
            continue
        key, raw_value = match.groups()
        value = raw_value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values, content[end + 5 :]


def count_lines(content: str) -> int:
    """Count human-visible source lines consistently."""

    return len(content.splitlines())


def iter_markdown_files(root: Path) -> Iterable[Path]:
    """Yield canonical and support Markdown files in stable order."""

    yield root / "SKILL.md"
    yield root / "README.md"
    yield root / "AGENTS.md"
    yield from sorted((root / "references").glob("*.md"))


def resolve_local_target(root: Path, source: Path, raw_target: str) -> Path | None:
    """Resolve a local Markdown link while rejecting path escape."""

    target = raw_target.split("#", 1)[0].strip()
    if not target or target.startswith("#"):
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None

    if target.startswith(("references/", "scripts/", "evals/", "agents/", "assets/", "templates/")):
        resolved = (root / target).resolve()
    else:
        resolved = (source.parent / target).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return Path("__ESCAPES_SKILL_ROOT__")
    return resolved


def validate_local_links(root: Path, report: ValidationReport) -> None:
    """Verify Markdown links and inline package paths."""

    for markdown_path in iter_markdown_files(root):
        if not markdown_path.is_file():
            continue
        content = markdown_path.read_text(encoding="utf-8")
        targets = [match.group(1) for match in LOCAL_LINK_PATTERN.finditer(content)]
        targets.extend(match.group(1) for match in INLINE_PATH_PATTERN.finditer(content))
        for target in sorted(set(targets)):
            resolved = resolve_local_target(root, markdown_path, target)
            if resolved is None:
                continue
            report.metrics["local_links_checked"] += 1
            if resolved.name == "__ESCAPES_SKILL_ROOT__":
                report.error(f"Local link escapes the skill root in {markdown_path.name}: {target}")
            elif not resolved.exists():
                relative_source = markdown_path.relative_to(root)
                report.error(f"Missing local link from {relative_source}: {target}")


def validate_frontmatter(root: Path, content: str, report: ValidationReport) -> None:
    """Validate portable name and description fields."""

    frontmatter, body = parse_frontmatter(content)
    if frontmatter is None:
        report.error("SKILL.md has no valid YAML frontmatter.")
        return

    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if name != root.name:
        report.error(f"Frontmatter name '{name}' does not match directory '{root.name}'.")
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) is None:
        report.error(f"Frontmatter name '{name}' is not a portable skill name.")
    if not description:
        report.error("Frontmatter description is missing.")
    elif len(description) > 1024:
        report.error(f"Frontmatter description exceeds 1024 characters ({len(description)}).")

    report.metrics["skill_md_lines"] = count_lines(content)
    if count_lines(body) > 500:
        report.error("SKILL.md body exceeds the 500-line release ceiling.")


def validate_json_metadata(root: Path, report: ValidationReport) -> None:
    """Validate thin package metadata without duplicating SKILL behavior."""

    raw = load_json(root / "metadata.json", report)
    data = string_keyed_mapping(raw)
    if raw is not None and data is None:
        report.error("metadata.json must contain a JSON object.")
        return
    if data is None:
        return
    for field_name in ("version", "organization", "date", "abstract"):
        if not isinstance(data.get(field_name), str) or not str(data[field_name]).strip():
            report.error(f"metadata.json is missing non-empty string field '{field_name}'.")


def validate_evals(root: Path, report: ValidationReport) -> None:
    """Validate behavioral eval structure, fixtures, tags, and assertions."""

    raw = load_json(root / "evals" / "evals.json", report)
    data = string_keyed_mapping(raw)
    if raw is not None and data is None:
        report.error("evals/evals.json must contain a JSON object.")
        return
    if data is None:
        return
    if data.get("skill_name") != root.name:
        report.error("evals/evals.json skill_name must match the directory.")

    eval_values = data.get("evals")
    if not isinstance(eval_values, list) or not eval_values:
        report.error("evals/evals.json must contain a non-empty evals array.")
        return

    seen_ids: set[int] = set()
    seen_tags: set[str] = set()
    report.metrics["eval_count"] = len(eval_values)
    for index, raw_eval in enumerate(eval_values):
        eval_item = string_keyed_mapping(raw_eval)
        if eval_item is None:
            report.error(f"Eval at index {index} must be an object.")
            continue
        label = eval_item.get("name") if isinstance(eval_item.get("name"), str) else f"index-{index}"

        eval_id = eval_item.get("id")
        if not isinstance(eval_id, int) or isinstance(eval_id, bool):
            report.error(f"Eval '{label}' has a non-integer id.")
        elif eval_id in seen_ids:
            report.error(f"Eval '{label}' duplicates id {eval_id}.")
        else:
            seen_ids.add(eval_id)

        for field_name in ("name", "prompt", "expected_output"):
            value = eval_item.get(field_name)
            if not isinstance(value, str) or not value.strip():
                report.error(f"Eval '{label}' is missing non-empty field '{field_name}'.")

        assertion_values = eval_item.get("assertions")
        if not isinstance(assertion_values, list) or not assertion_values:
            report.error(f"Eval '{label}' needs at least one typed assertion.")
        else:
            for assertion_index, raw_assertion in enumerate(assertion_values):
                assertion = string_keyed_mapping(raw_assertion)
                if assertion is None:
                    report.error(f"Eval '{label}' assertion {assertion_index} must be an object.")
                    continue
                for field_name in ("text", "type"):
                    value = assertion.get(field_name)
                    if not isinstance(value, str) or not value.strip():
                        report.error(
                            f"Eval '{label}' assertion {assertion_index} "
                            f"is missing non-empty field '{field_name}'."
                        )

        tag_values = eval_item.get("tags", [])
        if not isinstance(tag_values, list):
            report.error(f"Eval '{label}' tags must be an array.")
        else:
            for tag in tag_values:
                if isinstance(tag, str) and tag:
                    seen_tags.add(tag)
                else:
                    report.error(f"Eval '{label}' contains an invalid tag.")

        file_values = eval_item.get("files", [])
        if not isinstance(file_values, list):
            report.error(f"Eval '{label}' files must be an array.")
        else:
            for relative_file in file_values:
                if not isinstance(relative_file, str):
                    report.error(f"Eval '{label}' contains a non-string fixture path.")
                    continue
                resolved = (root / relative_file).resolve()
                try:
                    resolved.relative_to(root.resolve())
                except ValueError:
                    report.error(f"Eval '{label}' fixture escapes the skill root: {relative_file}")
                    continue
                if not resolved.is_file():
                    report.error(f"Eval '{label}' references missing fixture: {relative_file}")

    missing_tags = REQUIRED_EVAL_TAGS - seen_tags
    if missing_tags:
        report.error("Missing eval tag coverage: " + ", ".join(sorted(missing_tags)))


def validate_trigger_evals(root: Path, report: ValidationReport) -> None:
    """Validate realistic positive and adjacent-negative invocation queries."""

    raw = load_json(root / "evals" / "trigger-evals.json", report)
    if raw is None:
        return
    if not isinstance(raw, list):
        report.error("evals/trigger-evals.json must contain a JSON array.")
        return

    positives = 0
    negatives = 0
    queries: set[str] = set()
    report.metrics["trigger_eval_count"] = len(raw)
    for index, raw_item in enumerate(raw):
        item = string_keyed_mapping(raw_item)
        if item is None:
            report.error(f"Trigger eval at index {index} must be an object.")
            continue
        query = item.get("query")
        should_trigger = item.get("should_trigger")
        if not isinstance(query, str) or not query.strip():
            report.error(f"Trigger eval at index {index} has no non-empty query.")
        elif query in queries:
            report.error(f"Trigger eval query is duplicated: {query}")
        else:
            queries.add(query)
        if not isinstance(should_trigger, bool):
            report.error(f"Trigger eval at index {index} has non-boolean should_trigger.")
        elif should_trigger:
            positives += 1
        else:
            negatives += 1

    if len(raw) < 20:
        report.error("At least 20 trigger evals are required for release.")
    if positives < 8 or negatives < 8:
        report.error("Trigger evals need at least 8 positive and 8 negative near-miss cases.")


def validate_python(root: Path, report: ValidationReport) -> None:
    """Parse every shipped Python script without executing it."""

    for script_path in sorted((root / "scripts").glob("*.py")):
        report.metrics["python_files_checked"] += 1
        try:
            ast.parse(script_path.read_text(encoding="utf-8"), filename=str(script_path))
        except SyntaxError as exc:
            report.error(f"Python syntax error in {script_path.name}: {exc}")


def validate_skill(skill_path: str | Path) -> ValidationReport:
    """Run the complete local package validator."""

    root = Path(skill_path).resolve()
    report = ValidationReport()
    if not root.is_dir():
        report.error(f"Skill path does not exist: {root}")
        return report

    for relative_path in REQUIRED_FILES:
        if not (root / relative_path).is_file():
            report.error(f"Missing required file: {relative_path}")

    skill_path_obj = root / "SKILL.md"
    if not skill_path_obj.is_file():
        return report
    skill_text = skill_path_obj.read_text(encoding="utf-8")
    validate_frontmatter(root, skill_text, report)

    for phrase in REQUIRED_SKILL_PHRASES:
        if phrase not in skill_text:
            report.error(f"SKILL.md is missing release-critical phrase: {phrase}")

    if re.search(r"\]\(https?://(?:[^/]+\.)?namethatui\.com", skill_text, re.IGNORECASE):
        report.error("SKILL.md contains a clickable blocked-origin link.")

    manifest_text = (root / "agents" / "openai.yaml").read_text(encoding="utf-8") if (
        root / "agents" / "openai.yaml"
    ).is_file() else ""
    for manifest_key in ("interface:", "display_name:", "short_description:", "default_prompt:"):
        if manifest_key not in manifest_text:
            report.error(f"agents/openai.yaml is missing '{manifest_key}'.")

    for reference_path in sorted((root / "references").glob("*.md")):
        report.metrics["reference_count"] += 1
        if count_lines(reference_path.read_text(encoding="utf-8")) > 1000:
            report.error(f"Reference exceeds 1000 lines: {reference_path.name}")

    validate_local_links(root, report)
    validate_json_metadata(root, report)
    validate_evals(root, report)
    validate_trigger_evals(root, report)
    validate_python(root, report)
    return report


def main() -> None:
    """CLI entry point."""

    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        raise SystemExit(1)
    report = validate_skill(sys.argv[1])
    print(json.dumps(asdict(report), indent=2))
    raise SystemExit(0 if report.valid else 1)


if __name__ == "__main__":
    main()
