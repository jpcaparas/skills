#!/usr/bin/env python3
"""Validate the maintainable-tests skill package."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REQUIRED_DIRS = ["references", "scripts", "templates", "evals", "assets", "agents"]
REQUIRED_FILES = [
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "references/principles.md",
    "references/naming-and-intent.md",
    "references/structure-and-fixtures.md",
    "references/doubles-and-boundaries.md",
    "references/legacy-and-characterization.md",
    "references/side-effects-and-compatibility.md",
    "references/review-rubric.md",
    "references/gotchas.md",
    "references/source-notes.md",
    "scripts/analyze_maintainable_tests.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "templates/test-review.md",
    "evals/evals.json",
]
REQUIRED_SKILL_TERMS = [
    "living documentation",
    "onboarding",
    "edge cases",
    "legacy behavior",
    "Arrange",
    "Act",
    "Assert",
    "DAMP",
    "test doubles",
    "production boundary",
    "side effects",
    "compatibility",
    "false positive",
]
REQUIRED_SOURCE_URLS = [
    "https://pestphp.com/docs/writing-tests",
    "https://pestphp.com/docs/datasets",
    "https://docs.phpunit.de/en/12.5/fixtures.html",
    "https://docs.phpunit.de/en/12.5/test-doubles.html",
    "https://docs.phpunit.de/en/12.5/risky-tests.html",
    "https://testing.googleblog.com/2019/12/testing-on-toilet-tests-too-dry-make.html",
    "https://martinfowler.com/testing/",
    "https://martinfowler.com/articles/practical-test-pyramid.html",
    "https://github.com/nunomaduro/essentials/tree/bad47a6653a035ef8033856f0c4af3b65a704293",
]
REQUIRED_EVAL_TAGS = {
    "smoke",
    "edge",
    "negative",
    "disclosure",
    "legacy",
    "boundary",
    "review",
    "effects",
    "isolation",
    "compatibility",
}

SIDE_EFFECT_REQUIRED_HEADINGS = [
    "## Deny Unintended Effects",
    "## Reset Global Framework State",
    "## Test Configuration As A Decision Matrix",
    "## Exercise Compatibility Branches",
    "## Audit Assertion Subjects",
]

ALLOWED_ASSERTION_TYPES = {
    "functional",
    "structural",
    "disclosure",
    "negative",
    "verification",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_frontmatter(content: str) -> dict[str, str]:
    if not content.startswith("---\n"):
        return {}
    end = content.find("\n---", 4)
    if end == -1:
        return {}
    frontmatter = content[4:end]
    parsed: dict[str, str] = {}
    for line in frontmatter.splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if match:
            value = match.group(2).strip()
            if len(value) >= 2 and value[0] in {"'", '"'} and value[-1] == value[0]:
                value = value[1:-1]
            parsed[match.group(1)] = value
    return parsed


def strip_code_fences(content: str) -> str:
    return re.sub(r"```[\s\S]*?```", "", content)


def extract_references(content: str) -> set[str]:
    refs: set[str] = set()
    stripped = strip_code_fences(content)
    placeholder = re.compile(r"[{}<>]|\s")
    patterns = [
        re.compile(r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`"),
        re.compile(r"\[[^\]]+\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)"),
    ]
    for pattern in patterns:
        for match in pattern.finditer(stripped):
            ref = match.group(1)
            if not placeholder.search(ref):
                refs.add(ref)
    return refs


def validate(root: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    if not root.exists() or not root.is_dir():
        return {"valid": False, "errors": [f"not a directory: {root}"], "warnings": [], "metrics": metrics}

    for directory in REQUIRED_DIRS:
        if not (root / directory).is_dir():
            errors.append(f"missing directory: {directory}/")

    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing file: {relative}")

    skill_md = root / "SKILL.md"
    if skill_md.is_file():
        content = read_text(skill_md)
        metrics["skill_md_lines"] = len(content.splitlines())
        metrics["total_lines"] += metrics["skill_md_lines"]
        frontmatter = parse_frontmatter(content)
        if frontmatter.get("name") != root.name:
            errors.append("frontmatter name must match directory name")
        description = frontmatter.get("description", "")
        if not description:
            errors.append("frontmatter description is required")
        elif len(description) > 1024:
            errors.append("frontmatter description exceeds 1024 characters")
        if "Passive Trigger" not in content:
            errors.append("SKILL.md must document passive trigger behavior")
        for phrase in REQUIRED_SKILL_TERMS:
            if phrase.lower() not in content.lower():
                errors.append(f"SKILL.md must cover maintainable-test concept: {phrase}")
        for expected_ref in [
            "references/doubles-and-boundaries.md",
            "references/legacy-and-characterization.md",
            "references/side-effects-and-compatibility.md",
            "references/review-rubric.md",
        ]:
            if expected_ref not in content:
                errors.append(f"SKILL.md must route to {expected_ref}")
        if "{{ skill:maintainable-code }}" not in content:
            errors.append("SKILL.md must use symbolic reference to {{ skill:maintainable-code }}")
        if metrics["skill_md_lines"] > 500:
            warnings.append("SKILL.md exceeds 500 lines")
        for ref in extract_references(content):
            if not (root / ref).exists():
                errors.append(f"SKILL.md reference does not exist: {ref}")

    refs_dir = root / "references"
    if refs_dir.is_dir():
        for path in refs_dir.rglob("*.md"):
            text = read_text(path)
            metrics["reference_count"] += 1
            line_count = len(text.splitlines())
            metrics["total_lines"] += line_count
            if "## See Also" not in text:
                errors.append(f"reference missing See Also section: {path.relative_to(root)}")
            if line_count > 300 and "## Table of Contents" not in text:
                errors.append(f"large reference without TOC: {path.relative_to(root)}")
            if line_count > 1000:
                warnings.append(f"large reference file: {path.relative_to(root)}")

    source_notes = root / "references" / "source-notes.md"
    if source_notes.is_file():
        source_text = read_text(source_notes)
        for url in REQUIRED_SOURCE_URLS:
            if url not in source_text:
                errors.append(f"references/source-notes.md missing source URL: {url}")

    side_effects = root / "references" / "side-effects-and-compatibility.md"
    if side_effects.is_file():
        side_effect_text = read_text(side_effects)
        for heading in SIDE_EFFECT_REQUIRED_HEADINGS:
            if heading not in side_effect_text:
                errors.append(
                    "references/side-effects-and-compatibility.md missing heading: "
                    + heading
                )

    evals_path = root / "evals" / "evals.json"
    if evals_path.is_file():
        try:
            evals = json.loads(read_text(evals_path))
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is invalid JSON: {exc}")
        else:
            if evals.get("skill_name") != root.name:
                errors.append("evals skill_name must match directory name")
            items = evals.get("evals", [])
            if not items:
                errors.append("evals/evals.json must contain at least one eval")
            tags = {tag for item in items for tag in item.get("tags", [])}
            missing = REQUIRED_EVAL_TAGS - tags
            if missing:
                errors.append(f"evals/evals.json missing tag coverage: {', '.join(sorted(missing))}")
            for item in items:
                for field in ["id", "name", "prompt", "expected_output", "assertions", "tags"]:
                    if field not in item:
                        errors.append(f"eval missing field {field}: {item.get('name', item)}")
                if not item.get("assertions"):
                    errors.append(f"eval has no assertions: {item.get('name', item)}")
                for file_ref in item.get("files", []):
                    candidate = (root / file_ref).resolve()
                    try:
                        candidate.relative_to(root.resolve())
                    except ValueError:
                        errors.append(f"eval file escapes skill root: {file_ref}")
                    else:
                        if not candidate.is_file():
                            errors.append(f"eval file does not exist: {file_ref}")
                for assertion in item.get("assertions", []):
                    if "text" not in assertion or "type" not in assertion:
                        errors.append(
                            f"eval assertion must include text and type: {item.get('name', item)}"
                        )
                    elif assertion["type"] not in ALLOWED_ASSERTION_TYPES:
                        errors.append(
                            f"eval assertion has invalid type: {assertion['type']}"
                        )
            required_eval_tags = {
                "review-false-positive-artifact-assertions": {"effects", "assertions", "disclosure"},
                "isolate-effects-across-supported-versions": {"isolation", "compatibility", "disclosure"},
                "negative-disposable-port-check": {"negative", "near-miss"},
            }
            evals_by_name = {item.get("name"): item for item in items}
            for name, required_tags in required_eval_tags.items():
                item = evals_by_name.get(name)
                if item is None:
                    errors.append(f"required eval is missing: {name}")
                    continue
                missing_tags = required_tags - set(item.get("tags", []))
                if missing_tags:
                    errors.append(
                        f"eval {name} missing required tags: {', '.join(sorted(missing_tags))}"
                    )

    metadata_path = root / "metadata.json"
    if metadata_path.is_file():
        try:
            metadata = json.loads(read_text(metadata_path))
        except json.JSONDecodeError as exc:
            errors.append(f"metadata.json is invalid JSON: {exc}")
        else:
            if metadata.get("name") != root.name:
                errors.append("metadata name must match directory name")

    return {"valid": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("Usage: python3 scripts/validate.py <skill-path>", file=sys.stderr)
        return 1
    result = validate(Path(argv[0]).expanduser().resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
