#!/usr/bin/env python3
"""Validate the adversarial-test-sweep package and its release evidence."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit


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
    "scripts/test_validator_regressions.py",
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
MARKDOWN_LINK_RE = re.compile(
    r"!?\[[^\]]*\]\((?:<(?P<angle>[^>]+)>|(?P<plain>[^\s)]+))"
)
EVAL_FIXTURE_MANIFEST: dict[str, tuple[str, ...]] = {
    "parser-hardening-sweep": (
        "evals/fixtures/parser-weak-oracle/CONTRACT.md",
        "evals/fixtures/parser-weak-oracle/invoice_parser.py",
        "evals/fixtures/parser-weak-oracle/test_invoice_parser.py",
    )
}
FIXTURE_SHA256 = {
    "evals/fixtures/parser-weak-oracle/CONTRACT.md": (
        "8c988d58c0bad697abba5898e46ece6e84accbb9ca87b32b945031fd760d8bf0"
    ),
    "evals/fixtures/parser-weak-oracle/invoice_parser.py": (
        "df601e498bcbc40137eaa5d0b722e3095d719f658d5ce65767cc14b5c57d1c0c"
    ),
    "evals/fixtures/parser-weak-oracle/test_invoice_parser.py": (
        "c84c52275e3cd2d99bdd0c0152dc97c918e885cb9d7a891d6f82382397379c98"
    ),
    "evals/fixtures/parser-weak-oracle/check_duplicate_header.py": (
        "bce0e156b9d9e5d54422177d9d7c9b205a56a6a50b4e6286ae94cd78e803b748"
    ),
}
REVIEWED_EVIDENCE_SHA256 = {
    "scripts/test_skill.py": (
        "e9342a901f81c3385fcccf2b23a60f5c3a0aaeca447df66a334905a7bb7d202e"
    ),
    "scripts/test_validator_regressions.py": (
        "12b75a7a776b3b86566c926fcd300bf72caa3e88df5d663478c331b23b8fe319"
    ),
}
AGENT_INTERFACE_FIELDS = (
    "display_name",
    "short_description",
    "default_prompt",
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


def read_text_checked(path: Path, report: ValidationReport) -> str | None:
    """Read one text file and retain decoding or filesystem failures as evidence."""

    try:
        return read_text(path)
    except (OSError, UnicodeDecodeError) as exc:
        report.errors.append(f"cannot read UTF-8 text from {path}: {exc}")
        return None


def reject_json_constant(value: str) -> None:
    """Reject JavaScript numeric extensions that are not valid JSON."""

    raise ValueError(f"non-standard JSON constant: {value}")


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Build a JSON object while rejecting ambiguous duplicate members."""

    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON member: {key}")
        result[key] = value
    return result


def load_json(path: Path, report: ValidationReport) -> object | None:
    """Parse one JSON boundary and preserve a useful filename in failures."""

    try:
        return json.loads(
            read_text(path),
            object_pairs_hook=unique_json_object,
            parse_constant=reject_json_constant,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        report.errors.append(f"invalid JSON in {path.name}: {exc}")
        return None


def decode_yaml_scalar(raw_value: str) -> tuple[bool, str | None]:
    """Decode the dependency-free scalar subset used by this package."""

    value = raw_value.strip()
    if not value:
        return True, None
    if value.startswith('"'):
        try:
            decoded = json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return False, None
        return (True, decoded) if isinstance(decoded, str) else (False, None)
    if value.startswith("'"):
        if len(value) < 2 or not value.endswith("'"):
            return False, None
        inner = value[1:-1]
        decoded: list[str] = []
        index = 0
        while index < len(inner):
            if inner[index] != "'":
                decoded.append(inner[index])
                index += 1
                continue
            if index + 1 >= len(inner) or inner[index + 1] != "'":
                return False, None
            decoded.append("'")
            index += 2
        return True, "".join(decoded)
    if value.endswith(('"', "'")) or value.startswith(
        ("&", "*", "!", "[", "{", "|", ">", "#", "%", "@", "`")
    ):
        return False, None
    if re.search(r"\s#", value):
        value = value.split(" #", 1)[0].rstrip()
    if re.search(r":(?:\s|$)", value) or value.startswith(("- ", "? ", ": ")):
        return False, None
    if value.casefold() in {
        "null",
        "~",
        "true",
        "false",
        "yes",
        "no",
        "on",
        "off",
        ".nan",
        ".inf",
        "+.inf",
        "-.inf",
    }:
        return False, None
    return True, value


def normalized_text_sha256(path: Path) -> str:
    """Hash reviewed UTF-8 evidence independently of checkout line endings."""

    normalized_content = path.read_text(encoding="utf-8")
    return hashlib.sha256(normalized_content.encode("utf-8")).hexdigest()


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str, str]:
    """Parse the portable top-level scalar subset used by the skill package."""

    lines = content.splitlines()
    if not lines or lines[0] != "---":
        return None, "", content
    try:
        end_index = lines[1:].index("---") + 1
    except ValueError:
        return None, "", content

    frontmatter_lines = lines[1:end_index]
    frontmatter_text = "\n".join(frontmatter_lines)
    scalars: dict[str, str] = {}
    seen_keys: set[str] = set()
    nested_keys: dict[str, set[str]] = {"metadata": set(), "references": set()}
    current_container: str | None = None
    valid = True
    for line in frontmatter_lines:
        if "\t" in line:
            valid = False
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        if line.startswith("  - "):
            if current_container != "references":
                valid = False
                continue
            scalar_valid, value = decode_yaml_scalar(line[4:])
            if not scalar_valid or not value:
                valid = False
            elif value in nested_keys["references"]:
                valid = False
            else:
                nested_keys["references"].add(value)
            continue

        if line.startswith("  "):
            if current_container != "metadata":
                valid = False
                continue
            nested_match = re.match(r"^  ([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
            if nested_match is None:
                valid = False
                continue
            nested_key = nested_match.group(1)
            if nested_key != "version" or nested_key in nested_keys["metadata"]:
                valid = False
                continue
            nested_keys["metadata"].add(nested_key)
            scalar_valid, value = decode_yaml_scalar(nested_match.group(2))
            if not scalar_valid or not value:
                valid = False
            continue

        if line.startswith((" ", "-")):
            valid = False
            continue
        scalar_match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if scalar_match is None:
            valid = False
            continue
        key = scalar_match.group(1)
        if key in seen_keys:
            valid = False
            continue
        seen_keys.add(key)
        scalar_valid, value = decode_yaml_scalar(scalar_match.group(2))
        if not scalar_valid:
            valid = False
            current_container = None
            continue
        if value is None:
            if key not in nested_keys:
                valid = False
                current_container = None
            else:
                current_container = key
        else:
            scalars[key] = value
            current_container = None
    body = "\n".join(lines[end_index + 1 :])
    return (scalars if valid else None), frontmatter_text, body


def frontmatter_version(frontmatter_text: str) -> str | None:
    """Read only a direct two-space-indented ``metadata.version`` scalar."""

    lines = frontmatter_text.splitlines()
    try:
        metadata_index = lines.index("metadata:")
    except ValueError:
        return None

    version: str | None = None
    for line in lines[metadata_index + 1 :]:
        if line and not line.startswith((" ", "\t")):
            break
        match = re.match(r"^  version\s*:\s*(.*)$", line)
        if match is None:
            continue
        if version is not None:
            return None
        valid, decoded = decode_yaml_scalar(match.group(1))
        if not valid or not decoded:
            return None
        version = decoded
    return version


def validate_python(path: Path, report: ValidationReport) -> None:
    """Parse helper scripts without executing repository or network effects."""

    try:
        ast.parse(read_text(path), filename=str(path))
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        report.errors.append(f"Python syntax error in {path.name}: {exc}")


def markdown_local_references(content: str) -> set[str]:
    """Collect inline-code pointers and ordinary local Markdown destinations."""

    references = set(INLINE_PATH_RE.findall(content))
    for match in MARKDOWN_LINK_RE.finditer(content):
        raw_target = match.group("angle") or match.group("plain")
        if not raw_target or raw_target.startswith("#"):
            continue
        parsed = urlsplit(raw_target)
        if parsed.scheme or parsed.netloc:
            continue
        local_path = parsed.path
        if local_path:
            references.add(local_path)
    return references


def validate_local_references(root: Path, report: ValidationReport) -> None:
    """Resolve local Markdown pointers from the file that owns each pointer."""

    markdown_paths = [
        path
        for path in root.rglob("*.md")
        if path.is_file() and ".git" not in path.parts
    ]
    for markdown_path in markdown_paths:
        content = read_text_checked(markdown_path, report)
        if content is None:
            continue
        for raw_reference in sorted(markdown_local_references(content)):
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
                    "local reference escapes package: "
                    f"{markdown_path.relative_to(root)} -> {raw_reference}"
                )
                continue
            if not candidate.is_file():
                report.errors.append(
                    "missing or non-file local reference: "
                    f"{markdown_path.relative_to(root)} -> {raw_reference}"
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
    seen_prompts: set[str] = set()
    seen_assertions: set[tuple[str, str]] = set()
    observed_tags: set[str] = set()
    verified_fixture_cases: set[str] = set()

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

        raw_name = case.get("name")
        case_name: str | None = None
        if not isinstance(raw_name, str) or not raw_name.strip():
            report.errors.append(f"{label} name must be a non-empty string")
        elif raw_name in seen_names:
            report.errors.append(f"duplicate eval name: {raw_name}")
        else:
            case_name = raw_name
            seen_names.add(raw_name)
            label = f"eval {raw_name!r}"

        for field_name in ("prompt", "expected_output"):
            value = case.get(field_name)
            if not isinstance(value, str) or not value.strip():
                report.errors.append(f"{label} {field_name} must be a non-empty string")
            elif field_name == "prompt":
                normalized_prompt = " ".join(value.split()).casefold()
                if normalized_prompt in seen_prompts:
                    report.errors.append(f"{label} duplicates another eval prompt")
                else:
                    seen_prompts.add(normalized_prompt)

        tags = string_list(case.get("tags"))
        if not tags:
            report.errors.append(f"{label} tags must be a non-empty string array")
        else:
            observed_tags.update(tags)
            if len(tags) != len(set(tags)):
                report.errors.append(f"{label} tags must not contain duplicates")
            if any(not tag.strip() or tag != tag.strip() for tag in tags):
                report.errors.append(f"{label} tags must be trimmed non-empty strings")

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
                if isinstance(text, str) and isinstance(assertion_type, str):
                    assertion_key = (assertion_type, " ".join(text.split()).casefold())
                    if assertion_key in seen_assertions:
                        report.errors.append(
                            f"{label} assertion #{assertion_index} duplicates another assertion"
                        )
                    else:
                        seen_assertions.add(assertion_key)
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
            expected_files = EVAL_FIXTURE_MANIFEST.get(case_name or "")
            if expected_files is None:
                report.errors.append(
                    f"{label} uses fixture files without a reviewed fixture manifest"
                )
            elif tuple(file_references) != expected_files:
                report.errors.append(
                    f"{label} fixture files must exactly match the reviewed public manifest"
                )
            else:
                verified_fixture_cases.add(case_name or "")
        for relative_path in file_references:
            unresolved_candidate = root / relative_path
            candidate = unresolved_candidate.resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                report.errors.append(f"{label} fixture escapes package: {relative_path}")
            else:
                if unresolved_candidate.is_symlink():
                    report.errors.append(f"{label} fixture must not be a symlink: {relative_path}")
                elif not candidate.is_file():
                    report.errors.append(f"{label} fixture does not exist: {relative_path}")

    missing_tags = REQUIRED_EVAL_TAGS - observed_tags
    if missing_tags:
        report.errors.append("missing behavioral eval tags: " + ", ".join(sorted(missing_tags)))
    if report.metrics["fixture_eval_count"] < 1:
        report.errors.append("at least one behavioral eval must use committed fixture files")
    missing_fixture_cases = set(EVAL_FIXTURE_MANIFEST) - verified_fixture_cases
    if missing_fixture_cases:
        report.errors.append(
            "missing reviewed fixture evidence for evals: "
            + ", ".join(sorted(missing_fixture_cases))
        )


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
        else:
            normalized_query = " ".join(query.split()).casefold()
            if normalized_query in seen_queries:
                report.errors.append(f"duplicate trigger query: {query}")
            else:
                seen_queries.add(normalized_query)
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
    elif re.fullmatch(
        r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)",
        metadata_version,
    ) is None:
        report.errors.append("metadata.json version must use MAJOR.MINOR.PATCH")
    elif skill_version != metadata_version:
        report.errors.append("metadata.json version must match SKILL.md metadata.version")
    for field_name in ("display_name", "license", "description"):
        value = payload.get(field_name)
        if not isinstance(value, str) or not value.strip():
            report.errors.append(f"metadata.json {field_name} must be a non-empty string")
    for field_name in ("tags", "references"):
        values = string_list(payload.get(field_name))
        if not values or any(not value.strip() for value in values):
            report.errors.append(
                f"metadata.json {field_name} must be a non-empty string array"
            )
        elif len(values) != len(set(values)):
            report.errors.append(f"metadata.json {field_name} must not contain duplicates")


def parse_agent_interface(content: str) -> dict[str, str] | None:
    """Parse the package's small ``agents/openai.yaml`` interface mapping."""

    lines = content.splitlines()
    first_content_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip() and not line.lstrip().startswith("#")
        ),
        None,
    )
    if first_content_index is None or lines[first_content_index] != "interface:":
        return None

    fields: dict[str, str] = {}
    for line in lines[first_content_index + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.match(r"^  ([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if match is None:
            return None
        field_name = match.group(1)
        if field_name in fields:
            return None
        valid, value = decode_yaml_scalar(match.group(2))
        if not valid or value is None:
            return None
        fields[field_name] = value
    return fields


def validate_completion_gates(body: str, report: ValidationReport) -> None:
    """Require one observable completion gate inside each numbered phase."""

    workflow_match = re.search(
        r"^## Operating workflow\s*$\n(?P<workflow>.*?)(?=^## |\Z)",
        body,
        re.MULTILINE | re.DOTALL,
    )
    if workflow_match is None:
        report.errors.append("SKILL.md is missing a parseable operating workflow")
        return

    workflow = workflow_match.group("workflow")
    phase_matches = list(re.finditer(r"^### ([1-9])\.\s+", workflow, re.MULTILINE))
    phase_numbers = [int(match.group(1)) for match in phase_matches]
    if phase_numbers != list(range(1, 10)):
        report.errors.append("operating workflow must contain numbered phases 1 through 9")
        return

    for index, phase_match in enumerate(phase_matches):
        end = phase_matches[index + 1].start() if index + 1 < len(phase_matches) else len(workflow)
        phase = workflow[phase_match.start() : end]
        marker_count = phase.count("**Complete when:**")
        if marker_count != 1:
            report.errors.append(
                "operating workflow phase "
                f"{phase_match.group(1)} must contain exactly one completion gate"
            )


def validate_skill(skill_path: str) -> dict[str, object]:
    """Run every deterministic package check without modifying the target."""

    root = Path(skill_path).expanduser().resolve()
    report = ValidationReport()
    if not root.is_dir():
        report.errors.append(f"not a directory: {root}")
        return report.as_dict()

    for relative_path in REQUIRED_FILES:
        candidate = root / relative_path
        if candidate.is_symlink():
            report.errors.append(f"required package file must not be a symlink: {relative_path}")
        elif not candidate.is_file():
            report.errors.append(f"missing required file: {relative_path}")

    reviewed_files = FIXTURE_SHA256 | REVIEWED_EVIDENCE_SHA256
    for relative_path, expected_digest in reviewed_files.items():
        reviewed_path = root / relative_path
        if not reviewed_path.is_file() or reviewed_path.is_symlink():
            continue
        try:
            observed_digest = normalized_text_sha256(reviewed_path)
        except (OSError, UnicodeDecodeError) as exc:
            report.errors.append(f"cannot hash reviewed evidence {relative_path}: {exc}")
            continue
        if observed_digest != expected_digest:
            report.errors.append(f"reviewed evidence content changed: {relative_path}")

    skill_path_obj = root / "SKILL.md"
    if not skill_path_obj.is_file() or skill_path_obj.is_symlink():
        return report.as_dict()

    skill_content = read_text_checked(skill_path_obj, report)
    if skill_content is None:
        return report.as_dict()
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
        elif re.fullmatch(
            r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)",
            skill_version,
        ) is None:
            report.errors.append("SKILL.md metadata.version must use MAJOR.MINOR.PATCH")

    if len(body.splitlines()) > 500:
        report.errors.append("SKILL.md body exceeds the 500-line release ceiling")
    for heading in REQUIRED_HEADINGS:
        if heading not in body:
            report.errors.append(f"SKILL.md missing heading: {heading}")
    for term in REQUIRED_TERMS:
        if term.casefold() not in body.casefold():
            report.errors.append(f"SKILL.md missing required concept: {term}")
    validate_completion_gates(body, report)

    reference_contents: list[str] = []
    for relative_path in (
        "references/adversarial-techniques.md",
        "references/suite-evidence.md",
    ):
        reference_path = root / relative_path
        if not reference_path.is_file() or reference_path.is_symlink():
            continue
        content = read_text_checked(reference_path, report)
        if content is not None:
            reference_contents.append(content)
    reference_text = "\n".join(reference_contents)
    report.metrics["reference_count"] = len(reference_contents)
    for source_fragment in REQUIRED_SOURCE_FRAGMENTS:
        if source_fragment not in reference_text:
            report.errors.append(f"research references missing source: {source_fragment}")

    for markdown_path in root.rglob("*.md"):
        content = read_text_checked(markdown_path, report)
        if content is None:
            continue
        if AUTHORING_MARKER_RE.search(content):
            report.errors.append(
                f"unresolved authoring marker in {markdown_path.relative_to(root)}"
            )
        if markdown_path.parent.name == "references" and "## See also" not in content:
            report.errors.append(
                "reference missing See also section: "
                f"{markdown_path.relative_to(root)}"
            )
        if len(content.splitlines()) > 1000:
            report.errors.append(
                f"Markdown file exceeds 1000 lines: {markdown_path.relative_to(root)}"
            )

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
        manifest_content = read_text_checked(manifest_path, report)
        interface = (
            parse_agent_interface(manifest_content)
            if manifest_content is not None
            else None
        )
        if interface is None:
            report.errors.append("agents/openai.yaml must contain valid portable interface YAML")
        else:
            for field_name in AGENT_INTERFACE_FIELDS:
                value = interface.get(field_name)
                if not value or not value.strip():
                    report.errors.append(
                        f"agents/openai.yaml {field_name} must be a non-empty string"
                    )

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
