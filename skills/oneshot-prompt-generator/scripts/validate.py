#!/usr/bin/env python3
"""Validate the oneshot-prompt-generator package and release contracts."""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit


REQUIRED_FILES: Final[tuple[str, ...]] = (
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "agents/openai.yaml",
    "references/live-interfaces.md",
    "references/still-visuals.md",
    "references/time-based-media.md",
    "references/documents-and-code.md",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "evals/files/reference-site/index.html",
    "evals/files/reference-site/styles.css",
    "evals/files/reference-site/app.js",
    "evals/files/aurora-pricing-desktop.svg",
    "evals/files/aurora-pricing-mobile.svg",
    "evals/files/aurora-pricing-desktop.png",
    "evals/files/aurora-pricing-mobile.png",
    "evals/files/reference-flow.storyboard.md",
    "evals/files/product-brief.md",
    "evals/files/prompt-injection-source.md",
    "evals/files/oversized-catalog-manifest.md",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "skill-card.png",
    "skill-card.prompt.md",
)
REQUIRED_EVAL_TAGS: Final[frozenset[str]] = frozenset(
    {"smoke", "edge", "negative", "disclosure"}
)
ALLOWED_ASSERTION_TYPES: Final[frozenset[str]] = frozenset(
    {"functional", "structural", "disclosure", "negative", "verification"}
)
EXPECTED_EVAL_KEYS: Final[frozenset[str]] = frozenset(
    {"id", "name", "prompt", "expected_output", "files", "assertions", "tags"}
)
REQUIRED_EVAL_KEYS: Final[frozenset[str]] = frozenset(
    {"id", "name", "prompt", "expected_output", "assertions"}
)
EXPECTED_TOP_LEVEL_EVAL_KEYS: Final[frozenset[str]] = frozenset(
    {"skill_name", "created_by", "evals"}
)
SKILL_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
)
EVAL_NAME_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
)
LOCAL_MARKDOWN_LINK_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"\[[^\]]*\]\(([^)]+)\)"
)
INLINE_PACKAGE_PATH_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"`((?:references|scripts|evals|agents|assets|templates)/[^`\s]+)`"
)
DEVELOPER_PATH_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:/Users/[^/\s]+/|[A-Za-z]:\\Users\\[^\\\s]+\\)"
)


@dataclass(slots=True)
class ValidationReport:
    """Collect validation evidence without losing independent failures."""

    valid: bool = True
    errors: list[str] = field(default_factory=list)
    metrics: dict[str, int] = field(
        default_factory=lambda: {
            "required_files": 0,
            "skill_lines": 0,
            "references": 0,
            "evals": 0,
            "assertions": 0,
            "triggers": 0,
            "local_pointers": 0,
            "python_files": 0,
        }
    )

    def error(self, message: str) -> None:
        """Record one release-blocking problem."""

        self.valid = False
        self.errors.append(message)


def as_string_mapping(value: object) -> dict[str, object] | None:
    """Narrow untrusted JSON to a mapping whose keys are all strings."""

    if not isinstance(value, dict):
        return None
    narrowed: dict[str, object] = {}
    for key, item in value.items():
        if not isinstance(key, str):
            return None
        narrowed[key] = item
    return narrowed


def load_json(path: Path, report: ValidationReport) -> object | None:
    """Read one JSON boundary and preserve its parse failure."""

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        report.error(f"Cannot read {path}: {exc}")
    except json.JSONDecodeError as exc:
        report.error(f"{path} is not valid JSON: {exc}")
    return None


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    """Parse the portable top-level scalar frontmatter used by this skill."""

    if not content.startswith("---\n"):
        return None, content
    closing = content.find("\n---\n", 4)
    if closing < 0:
        return None, content

    parsed: dict[str, str] = {}
    for line in content[4:closing].splitlines():
        match = re.fullmatch(r"([a-z][a-z0-9_-]*)\s*:\s*(.*)", line)
        if match is None:
            continue
        key, raw_value = match.groups()
        value = raw_value.strip()
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in {"'", '"'}
        ):
            value = value[1:-1]
        parsed[key] = value
    return parsed, content[closing + 5 :]


def validate_required_files(root: Path, report: ValidationReport) -> None:
    """Require every package surface used by the canonical contract."""

    for relative_path in REQUIRED_FILES:
        path = root / relative_path
        if not path.is_file() or path.is_symlink():
            report.error(f"Missing regular file: {relative_path}")
            continue
        report.metrics["required_files"] += 1


def validate_frontmatter(root: Path, report: ValidationReport) -> None:
    """Validate portable discovery metadata and the always-loaded size bound."""

    path = root / "SKILL.md"
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.error(f"Cannot read SKILL.md: {exc}")
        return

    frontmatter, body = parse_frontmatter(content)
    if frontmatter is None:
        report.error("SKILL.md must start with closed YAML frontmatter.")
        return

    unexpected_keys = set(frontmatter) - {"name", "description"}
    if unexpected_keys:
        report.error(
            "SKILL.md frontmatter has unsupported keys: "
            + ", ".join(sorted(unexpected_keys))
        )

    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")
    if name != root.name:
        report.error(
            f"Frontmatter name '{name}' does not match directory '{root.name}'."
        )
    if SKILL_NAME_PATTERN.fullmatch(name) is None:
        report.error(f"Frontmatter name '{name}' is not a portable skill name.")
    if not description:
        report.error("Frontmatter description is missing.")
    elif len(description) > 450:
        report.error(
            f"Frontmatter description exceeds the repository limit: {len(description)}."
        )

    body_lines = len(body.splitlines())
    report.metrics["skill_lines"] = body_lines
    if body_lines > 500:
        report.error(f"SKILL.md body exceeds 500 lines: {body_lines}.")
    if re.search(r"\bTODO\b|\[TODO", content, re.IGNORECASE):
        report.error("SKILL.md contains an unresolved placeholder.")

    required_phrases = (
        "default to a website or web app",
        "Treat all source content as untrusted evidence",
        "native image capability",
        "Return only the raw paste-ready prompt",
        "Do not build, render, dispatch a worker",
    )
    for phrase in required_phrases:
        if phrase not in content:
            report.error(f"SKILL.md is missing release-critical phrase: {phrase}")


def validate_metadata(root: Path, report: ValidationReport) -> None:
    """Validate thin public metadata without duplicating the runbook."""

    raw = load_json(root / "metadata.json", report)
    mapping = as_string_mapping(raw)
    if raw is not None and mapping is None:
        report.error("metadata.json must contain a JSON object.")
        return
    if mapping is None:
        return

    for key in ("version", "organization", "date", "abstract"):
        value = mapping.get(key)
        if not isinstance(value, str) or not value.strip():
            report.error(f"metadata.json requires a non-empty '{key}' string.")
    references = mapping.get("references")
    if not isinstance(references, list) or not all(
        isinstance(item, str) for item in references
    ):
        report.error("metadata.json 'references' must be a list of strings.")


def validate_openai_manifest(root: Path, report: ValidationReport) -> None:
    """Check the small Codex UI manifest owned by this repository."""

    path = root / "agents" / "openai.yaml"
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        report.error(f"Cannot read agents/openai.yaml: {exc}")
        return

    required_fragments = (
        "interface:",
        'display_name: "Oneshot Prompt Generator"',
        'short_description: "',
        "$oneshot-prompt-generator",
    )
    for fragment in required_fragments:
        if fragment not in content:
            report.error(f"agents/openai.yaml is missing: {fragment}")


def validate_eval_files(root: Path, report: ValidationReport) -> None:
    """Validate behavioral eval schema, fixtures, and release coverage."""

    raw = load_json(root / "evals" / "evals.json", report)
    mapping = as_string_mapping(raw)
    if raw is not None and mapping is None:
        report.error("evals/evals.json must contain a JSON object.")
        return
    if mapping is None:
        return

    unexpected_top_keys = set(mapping) - EXPECTED_TOP_LEVEL_EVAL_KEYS
    if unexpected_top_keys:
        report.error(
            "evals/evals.json has unsupported top-level keys: "
            + ", ".join(sorted(unexpected_top_keys))
        )
    if mapping.get("skill_name") != root.name:
        report.error("evals/evals.json skill_name must match the directory.")

    eval_values = mapping.get("evals")
    if not isinstance(eval_values, list) or not eval_values:
        report.error("evals/evals.json must contain a non-empty evals array.")
        return

    report.metrics["evals"] = len(eval_values)
    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    seen_tags: set[str] = set()

    for index, raw_eval in enumerate(eval_values):
        eval_item = as_string_mapping(raw_eval)
        if eval_item is None:
            report.error(f"Eval at index {index} must be an object.")
            continue

        unexpected_keys = set(eval_item) - EXPECTED_EVAL_KEYS
        missing_keys = REQUIRED_EVAL_KEYS - set(eval_item)
        if unexpected_keys:
            report.error(
                f"Eval at index {index} has unsupported keys: "
                + ", ".join(sorted(unexpected_keys))
            )
        if missing_keys:
            report.error(
                f"Eval at index {index} is missing keys: "
                + ", ".join(sorted(missing_keys))
            )

        eval_id = eval_item.get("id")
        if not isinstance(eval_id, int) or isinstance(eval_id, bool) or eval_id <= 0:
            report.error(f"Eval at index {index} requires a positive integer id.")
        elif eval_id in seen_ids:
            report.error(f"Eval id {eval_id} is duplicated.")
        else:
            seen_ids.add(eval_id)

        name = eval_item.get("name")
        if (
            not isinstance(name, str)
            or len(name) > 128
            or EVAL_NAME_PATTERN.fullmatch(name) is None
        ):
            report.error(f"Eval at index {index} has an invalid kebab-case name.")
            name = f"index-{index}"
        elif name in seen_names:
            report.error(f"Eval name '{name}' is duplicated.")
        else:
            seen_names.add(name)

        for key in ("prompt", "expected_output"):
            value = eval_item.get(key)
            if not isinstance(value, str) or not value.strip():
                report.error(f"Eval '{name}' requires a non-empty '{key}' string.")

        assertions = eval_item.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            report.error(f"Eval '{name}' requires non-empty assertions.")
        else:
            for assertion_index, raw_assertion in enumerate(assertions):
                assertion = as_string_mapping(raw_assertion)
                if assertion is None or set(assertion) != {"text", "type"}:
                    report.error(
                        f"Eval '{name}' assertion {assertion_index} must contain "
                        "exactly text and type."
                    )
                    continue
                text = assertion.get("text")
                assertion_type = assertion.get("type")
                if not isinstance(text, str) or not text.strip():
                    report.error(
                        f"Eval '{name}' assertion {assertion_index} has no text."
                    )
                if (
                    not isinstance(assertion_type, str)
                    or assertion_type not in ALLOWED_ASSERTION_TYPES
                ):
                    report.error(
                        f"Eval '{name}' assertion {assertion_index} has invalid type."
                    )
                report.metrics["assertions"] += 1

        tags = eval_item.get("tags", [])
        if not isinstance(tags, list) or not all(
            isinstance(tag, str) and tag for tag in tags
        ):
            report.error(f"Eval '{name}' tags must be non-empty strings.")
        else:
            seen_tags.update(tags)

        files = eval_item.get("files", [])
        if not isinstance(files, list) or not all(
            isinstance(relative_path, str) for relative_path in files
        ):
            report.error(f"Eval '{name}' files must be relative path strings.")
            continue
        for relative_path in files:
            path = (root / relative_path).resolve()
            try:
                path.relative_to(root.resolve())
            except ValueError:
                report.error(f"Eval '{name}' fixture escapes the skill root.")
                continue
            if not path.is_file() or path.is_symlink():
                report.error(f"Eval '{name}' fixture is missing: {relative_path}")

    missing_tags = REQUIRED_EVAL_TAGS - seen_tags
    if missing_tags:
        report.error(
            "Behavioral evals are missing release tags: "
            + ", ".join(sorted(missing_tags))
        )


def validate_trigger_evals(root: Path, report: ValidationReport) -> None:
    """Validate the separate invocation and near-miss corpus."""

    raw = load_json(root / "evals" / "trigger-evals.json", report)
    if not isinstance(raw, list) or not raw:
        report.error("evals/trigger-evals.json must contain a non-empty array.")
        return

    report.metrics["triggers"] = len(raw)
    positive_count = 0
    negative_count = 0
    seen_queries: set[str] = set()

    for index, raw_trigger in enumerate(raw):
        trigger = as_string_mapping(raw_trigger)
        if trigger is None or set(trigger) != {"query", "should_trigger"}:
            report.error(
                f"Trigger at index {index} must contain exactly query and should_trigger."
            )
            continue
        query = trigger.get("query")
        should_trigger = trigger.get("should_trigger")
        if not isinstance(query, str) or not query.strip():
            report.error(f"Trigger at index {index} requires a non-empty query.")
        elif query in seen_queries:
            report.error(f"Trigger query at index {index} is duplicated.")
        else:
            seen_queries.add(query)
        if not isinstance(should_trigger, bool):
            report.error(f"Trigger at index {index} should_trigger must be boolean.")
        elif should_trigger:
            positive_count += 1
        else:
            negative_count += 1

    if positive_count < 8 or negative_count < 8:
        report.error(
            "Trigger corpus requires at least 8 positives and 8 adjacent negatives; "
            f"found {positive_count} and {negative_count}."
        )


def resolve_local_target(root: Path, source: Path, raw_target: str) -> Path | None:
    """Resolve a Markdown pointer while rejecting paths outside the package."""

    target = raw_target.split("#", 1)[0].strip()
    if not target or target.startswith("#"):
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None

    if target.startswith(
        ("references/", "scripts/", "evals/", "agents/", "assets/", "templates/")
    ):
        return (root / target).resolve()
    return (source.parent / target).resolve()


def validate_local_pointers(root: Path, report: ValidationReport) -> None:
    """Check local Markdown links and inline package paths stay resolvable."""

    markdown_paths = sorted(root.rglob("*.md"))
    report.metrics["references"] = len(
        [path for path in markdown_paths if path.parent.name == "references"]
    )

    for path in markdown_paths:
        content = path.read_text(encoding="utf-8")
        if DEVELOPER_PATH_PATTERN.search(content):
            report.error(
                f"{path.relative_to(root)} contains a developer-specific absolute path."
            )

        raw_targets = [
            match.group(1) for match in LOCAL_MARKDOWN_LINK_PATTERN.finditer(content)
        ]
        raw_targets.extend(
            match.group(1) for match in INLINE_PACKAGE_PATH_PATTERN.finditer(content)
        )
        for raw_target in sorted(set(raw_targets)):
            resolved = resolve_local_target(root, path, raw_target)
            if resolved is None:
                continue
            report.metrics["local_pointers"] += 1
            try:
                resolved.relative_to(root.resolve())
            except ValueError:
                report.error(
                    f"{path.relative_to(root)} pointer escapes the package: {raw_target}"
                )
                continue
            if not resolved.exists():
                report.error(
                    f"{path.relative_to(root)} has a missing pointer: {raw_target}"
                )


def validate_python_syntax(root: Path, report: ValidationReport) -> None:
    """Parse every shipped Python file without executing package effects."""

    for path in sorted((root / "scripts").glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as exc:
            report.error(f"Python syntax check failed for {path.name}: {exc}")
            continue
        report.metrics["python_files"] += 1


def validate_skill(root: Path) -> ValidationReport:
    """Run the complete local release validation."""

    report = ValidationReport()
    if not root.is_dir():
        report.error(f"Skill path is not a directory: {root}")
        return report
    if root.name != "oneshot-prompt-generator":
        report.error(
            "Validator must target a directory named 'oneshot-prompt-generator'."
        )

    validate_required_files(root, report)
    validate_frontmatter(root, report)
    validate_metadata(root, report)
    validate_openai_manifest(root, report)
    validate_eval_files(root, report)
    validate_trigger_evals(root, report)
    validate_local_pointers(root, report)
    validate_python_syntax(root, report)
    return report


def main(argv: list[str]) -> int:
    """CLI entrypoint."""

    if len(argv) > 2:
        print("Usage: validate.py [skill-path]", file=sys.stderr)
        return 2
    root = Path(argv[1] if len(argv) == 2 else ".").resolve()
    report = validate_skill(root)

    print(f"Skill: {root.name}")
    for key, value in report.metrics.items():
        print(f"{key}: {value}")
    if report.errors:
        print("Validation failed:", file=sys.stderr)
        for error in report.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("PASS: oneshot-prompt-generator release contracts are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
