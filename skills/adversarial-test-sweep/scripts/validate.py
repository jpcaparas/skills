#!/usr/bin/env python3
"""Validate the adversarial-test-sweep package and its release evidence."""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


REQUIRED_FILES = (
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "agents/openai.yaml",
    "references/adversarial-techniques.md",
    "references/suite-evidence.md",
    "templates/risk-ledger.md",
    "templates/sweep-report.md",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "evals/fixtures/parser-weak-oracle/CONTRACT.md",
    "evals/fixtures/parser-weak-oracle/invoice_parser.py",
    "evals/fixtures/parser-weak-oracle/test_invoice_parser.py",
    "evals/fixtures/parser-weak-oracle/check_duplicate_header.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "skill-card.prompt.md",
    "skill-card.png",
)
REQUIRED_HEADINGS = (
    "## Route the request",
    "## Non-negotiable evidence rules",
    "## Operating workflow",
    "## Gotchas",
    "## Reading guide",
)
REQUIRED_TERMS = (
    "risk ledger",
    "malformed",
    "state",
    "concurrency",
    "resource",
    "mutation",
    "coverage",
    "regression",
    "replay",
    "residual",
)
REQUIRED_SOURCE_FRAGMENTS = (
    "doi.org/10.6028/NIST.IR.8397",
    "doi.org/10.6028/NIST.SP.800-142",
    "doi.org/10.1145/351240.351266",
    "microsoft.com/en-us/research/publication/chess",
    "mutation-effectiveness-fse2014",
    "icse_2014_inozemtseva.pdf",
    "LuoETAL14FlakyTestsAnalysis.pdf",
    "doi.org/10.1109/32.988498",
)
REQUIRED_EVAL_TAGS = frozenset(
    {"smoke", "edge", "negative", "disclosure", "safety", "verification"}
)
ASSERTION_TYPES = frozenset(
    {"functional", "structural", "disclosure", "negative", "verification"}
)
AUTHORING_MARKER_RE = re.compile(r"\b(?:TODO|TBD|FIXME)(?=\b|:)")
INLINE_PATH_RE = re.compile(
    r"`((?:SKILL\.md|\.\./[^`\s]+|(?:references|templates|scripts|evals|agents)/[^`\s]+))`"
)


@dataclass(slots=True)
class ValidationReport:
    """Accumulate deterministic release failures and auditable package metrics."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, int] = field(
        default_factory=lambda: {
            "skill_md_lines": 0,
            "reference_count": 0,
            "cross_reference_count": 0,
            "eval_count": 0,
            "assertion_count": 0,
            "fixture_eval_count": 0,
            "fixture_file_count": 0,
            "negative_disclosure_assertion_count": 0,
            "trigger_eval_count": 0,
            "trigger_positive_count": 0,
            "trigger_negative_count": 0,
        }
    )

    def as_dict(self) -> dict[str, object]:
        """Return the stable machine-readable result consumed by repository checks."""

        return {
            "valid": not self.errors,
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics,
        }


def read_text(path: Path) -> str:
    """Read UTF-8 text so decoding errors fail the package check loudly."""

    return path.read_text(encoding="utf-8")


def load_json(path: Path, report: ValidationReport) -> object | None:
    """Parse one JSON boundary and preserve a useful filename in failures."""

    try:
        return json.loads(read_text(path))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        report.errors.append(f"invalid JSON in {path.name}: {exc}")
        return None


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str, str]:
    """Parse the portable top-level scalar subset and retain nested text for version checks."""

    match = re.match(r"^---\n(?P<frontmatter>.*?)\n---\n?(?P<body>.*)$", content, re.DOTALL)
    if match is None:
        return None, "", content

    frontmatter_text = match.group("frontmatter")
    scalars: dict[str, str] = {}
    for line in frontmatter_text.splitlines():
        if not line.strip() or line.startswith((" ", "\t", "-")):
            continue
        scalar_match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if scalar_match is None:
            continue
        value = scalar_match.group(2).strip()
        if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
            value = value[1:-1]
        scalars[scalar_match.group(1)] = value
    return scalars, frontmatter_text, match.group("body")


def frontmatter_version(frontmatter_text: str) -> str | None:
    """Read the repository-owned metadata.version without pretending to be a YAML parser."""

    match = re.search(
        r"^metadata:\s*\n(?:^[ \t]+[^\n]*\n)*?^[ \t]+version:\s*[\"']?([^\"'\s]+)[\"']?\s*$",
        frontmatter_text,
        re.MULTILINE,
    )
    return match.group(1) if match is not None else None


def validate_python(path: Path, report: ValidationReport) -> None:
    """Parse helper scripts without executing repository or network effects."""

    try:
        ast.parse(read_text(path), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        report.errors.append(f"Python syntax error in {path.name}: {exc}")


def validate_local_references(root: Path, report: ValidationReport) -> None:
    """Resolve local Markdown pointers from the file that owns each pointer."""

    markdown_paths = [
        path
        for path in root.rglob("*.md")
        if path.is_file() and ".git" not in path.parts
    ]
    for markdown_path in markdown_paths:
        content = read_text(markdown_path)
        for raw_reference in INLINE_PATH_RE.findall(content):
            report.metrics["cross_reference_count"] += 1
            # Package-root paths are the portable convention used by the
            # shared release validator; explicit ../ paths stay file-relative.
            if raw_reference == "SKILL.md" or raw_reference.startswith(
                ("references/", "templates/", "scripts/", "evals/", "agents/")
            ):
                candidate = (root / raw_reference).resolve()
            else:
                candidate = (markdown_path.parent / raw_reference).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                report.errors.append(
                    f"local reference escapes package: {markdown_path.relative_to(root)} -> {raw_reference}"
                )
                continue
            if not candidate.exists():
                report.errors.append(
                    f"missing local reference: {markdown_path.relative_to(root)} -> {raw_reference}"
                )


def string_list(value: object) -> list[str] | None:
    """Narrow an unknown JSON array to a homogeneous list of strings."""

    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        return None
    return [item for item in value if isinstance(item, str)]


def validate_behavior_evals(root: Path, report: ValidationReport) -> None:
    """Validate typed behavioral cases separately from invocation queries."""

    payload = load_json(root / "evals" / "evals.json", report)
    if not isinstance(payload, dict):
        report.errors.append("evals/evals.json must contain an object")
        return
    if payload.get("skill_name") != root.name:
        report.errors.append("evals/evals.json skill_name must match the directory name")

    cases = payload.get("evals")
    if not isinstance(cases, list) or not cases:
        report.errors.append("evals/evals.json must contain a non-empty evals array")
        return

    report.metrics["eval_count"] = len(cases)
    seen_ids: set[int] = set()
    seen_names: set[str] = set()
    observed_tags: set[str] = set()

    for index, case in enumerate(cases, start=1):
        label = f"eval #{index}"
        if not isinstance(case, dict):
            report.errors.append(f"{label} must be an object")
            continue

        case_id = case.get("id")
        if not isinstance(case_id, int) or isinstance(case_id, bool):
            report.errors.append(f"{label} id must be an integer")
        elif case_id in seen_ids:
            report.errors.append(f"duplicate eval id: {case_id}")
        else:
            seen_ids.add(case_id)

        name = case.get("name")
        if not isinstance(name, str) or not name.strip():
            report.errors.append(f"{label} name must be a non-empty string")
        elif name in seen_names:
            report.errors.append(f"duplicate eval name: {name}")
        else:
            seen_names.add(name)
            label = f"eval {name!r}"

        for field_name in ("prompt", "expected_output"):
            value = case.get(field_name)
            if not isinstance(value, str) or not value.strip():
                report.errors.append(f"{label} {field_name} must be a non-empty string")

        tags = string_list(case.get("tags"))
        if not tags:
            report.errors.append(f"{label} tags must be a non-empty string array")
        else:
            observed_tags.update(tags)

        assertions = case.get("assertions")
        has_positive_disclosure = False
        has_negative_disclosure = False
        if not isinstance(assertions, list) or not assertions:
            report.errors.append(f"{label} assertions must be a non-empty array")
        else:
            for assertion_index, assertion in enumerate(assertions, start=1):
                report.metrics["assertion_count"] += 1
                if not isinstance(assertion, dict):
                    report.errors.append(f"{label} assertion #{assertion_index} must be an object")
                    continue
                text = assertion.get("text")
                assertion_type = assertion.get("type")
                if not isinstance(text, str) or not text.strip():
                    report.errors.append(f"{label} assertion #{assertion_index} needs text")
                if assertion_type not in ASSERTION_TYPES:
                    report.errors.append(
                        f"{label} assertion #{assertion_index} has invalid type: {assertion_type!r}"
                    )
                if assertion_type == "disclosure" and isinstance(text, str):
                    if text.casefold().startswith("does not load "):
                        has_negative_disclosure = True
                        report.metrics["negative_disclosure_assertion_count"] += 1
                    else:
                        has_positive_disclosure = True

        if tags and "disclosure" in tags:
            if not has_positive_disclosure:
                report.errors.append(f"{label} needs a positive disclosure assertion")
            if not has_negative_disclosure:
                report.errors.append(f"{label} needs a negative disclosure assertion")

        files = case.get("files", [])
        file_references = string_list(files)
        if file_references is None:
            report.errors.append(f"{label} files must be a string array when present")
            continue
        if file_references:
            report.metrics["fixture_eval_count"] += 1
            report.metrics["fixture_file_count"] += len(file_references)
        for relative_path in file_references:
            candidate = (root / relative_path).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                report.errors.append(f"{label} fixture escapes package: {relative_path}")
            else:
                if not candidate.is_file():
                    report.errors.append(f"{label} fixture does not exist: {relative_path}")

    missing_tags = REQUIRED_EVAL_TAGS - observed_tags
    if missing_tags:
        report.errors.append("missing behavioral eval tags: " + ", ".join(sorted(missing_tags)))
    if report.metrics["fixture_eval_count"] < 1:
        report.errors.append("at least one behavioral eval must use committed fixture files")


def validate_trigger_evals(root: Path, report: ValidationReport) -> None:
    """Require balanced realistic invocation evidence with no duplicate queries."""

    payload = load_json(root / "evals" / "trigger-evals.json", report)
    if not isinstance(payload, list) or not payload:
        report.errors.append("evals/trigger-evals.json must contain a non-empty array")
        return

    report.metrics["trigger_eval_count"] = len(payload)
    seen_queries: set[str] = set()
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            report.errors.append(f"trigger eval #{index} must be an object")
            continue
        query = item.get("query")
        should_trigger = item.get("should_trigger")
        if not isinstance(query, str) or not query.strip():
            report.errors.append(f"trigger eval #{index} query must be a non-empty string")
        elif query in seen_queries:
            report.errors.append(f"duplicate trigger query: {query}")
        else:
            seen_queries.add(query)
        if not isinstance(should_trigger, bool):
            report.errors.append(f"trigger eval #{index} should_trigger must be boolean")
        elif should_trigger:
            report.metrics["trigger_positive_count"] += 1
        else:
            report.metrics["trigger_negative_count"] += 1

    if report.metrics["trigger_positive_count"] < 3:
        report.errors.append("trigger evals require at least three positive cases")
    if report.metrics["trigger_negative_count"] < 3:
        report.errors.append("trigger evals require at least three negative cases")


def validate_metadata(root: Path, skill_version: str | None, report: ValidationReport) -> None:
    """Keep packaging identity and the canonical skill version synchronized."""

    payload = load_json(root / "metadata.json", report)
    if not isinstance(payload, dict):
        report.errors.append("metadata.json must contain an object")
        return
    if payload.get("name") != root.name:
        report.errors.append("metadata.json name must match the directory name")
    if payload.get("entrypoint") != "SKILL.md":
        report.errors.append("metadata.json entrypoint must be SKILL.md")
    metadata_version = payload.get("version")
    if not isinstance(metadata_version, str) or not metadata_version:
        report.errors.append("metadata.json version must be a non-empty string")
    elif skill_version != metadata_version:
        report.errors.append("metadata.json version must match SKILL.md metadata.version")


def validate_skill(skill_path: str) -> dict[str, object]:
    """Run every deterministic package check without modifying the target."""

    root = Path(skill_path).expanduser().resolve()
    report = ValidationReport()
    if not root.is_dir():
        report.errors.append(f"not a directory: {root}")
        return report.as_dict()

    for relative_path in REQUIRED_FILES:
        if not (root / relative_path).is_file():
            report.errors.append(f"missing required file: {relative_path}")

    skill_path_obj = root / "SKILL.md"
    if not skill_path_obj.is_file():
        return report.as_dict()

    skill_content = read_text(skill_path_obj)
    report.metrics["skill_md_lines"] = len(skill_content.splitlines())
    scalars, frontmatter_text, body = parse_frontmatter(skill_content)
    if scalars is None:
        report.errors.append("SKILL.md is missing valid YAML frontmatter fences")
        skill_version = None
    else:
        if scalars.get("name") != root.name:
            report.errors.append("frontmatter name must match the directory name")
        description = scalars.get("description", "")
        if not description:
            report.errors.append("frontmatter description is required")
        elif len(description) > 1024:
            report.errors.append("frontmatter description exceeds 1024 characters")
        skill_version = frontmatter_version(frontmatter_text)
        if skill_version is None:
            report.errors.append("SKILL.md metadata.version is required")

    if len(body.splitlines()) > 500:
        report.errors.append("SKILL.md body exceeds the 500-line release ceiling")
    for heading in REQUIRED_HEADINGS:
        if heading not in body:
            report.errors.append(f"SKILL.md missing heading: {heading}")
    for term in REQUIRED_TERMS:
        if term.casefold() not in body.casefold():
            report.errors.append(f"SKILL.md missing required concept: {term}")
    if body.count("**Complete when:**") < 9:
        report.errors.append("every operating phase must have an observable completion criterion")

    reference_text = "\n".join(
        read_text(root / relative_path)
        for relative_path in (
            "references/adversarial-techniques.md",
            "references/suite-evidence.md",
        )
        if (root / relative_path).is_file()
    )
    report.metrics["reference_count"] = 2 if reference_text else 0
    for source_fragment in REQUIRED_SOURCE_FRAGMENTS:
        if source_fragment not in reference_text:
            report.errors.append(f"research references missing source: {source_fragment}")

    for markdown_path in root.rglob("*.md"):
        content = read_text(markdown_path)
        if AUTHORING_MARKER_RE.search(content):
            report.errors.append(f"unresolved authoring marker in {markdown_path.relative_to(root)}")
        if markdown_path.parent.name == "references" and "## See also" not in content:
            report.errors.append(f"reference missing See also section: {markdown_path.relative_to(root)}")
        if len(content.splitlines()) > 1000:
            report.errors.append(f"Markdown file exceeds 1000 lines: {markdown_path.relative_to(root)}")

    for script_path in (root / "scripts").glob("*.py"):
        validate_python(script_path, report)
    for fixture_path in (root / "evals" / "fixtures").rglob("*.py"):
        validate_python(fixture_path, report)

    validate_local_references(root, report)
    validate_behavior_evals(root, report)
    validate_trigger_evals(root, report)
    validate_metadata(root, skill_version, report)

    manifest_path = root / "agents" / "openai.yaml"
    if manifest_path.is_file():
        manifest = read_text(manifest_path)
        for field_name in ("interface:", "display_name:", "short_description:", "default_prompt:"):
            if field_name not in manifest:
                report.errors.append(f"agents/openai.yaml missing field: {field_name}")

    return report.as_dict()


def main(argv: list[str]) -> int:
    """Validate one explicit skill path and return a conventional exit status."""

    if len(argv) != 1:
        print("Usage: python3 scripts/validate.py <skill-path>", file=sys.stderr)
        return 2
    result = validate_skill(argv[0])
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
