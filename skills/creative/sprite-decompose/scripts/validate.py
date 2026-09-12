#!/usr/bin/env python3
"""Validate the sprite-decompose package and its deterministic contracts."""

from __future__ import annotations

import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from PIL import Image, UnidentifiedImageError

from sprite_decompose_core import SpecError, load_spec


REQUIRED_FILES = (
    "SKILL.md",
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "agents/openai.yaml",
    "references/region-review.md",
    "templates/regions.example.json",
    "requirements.txt",
    "pyrightconfig.json",
    "scripts/sprite_decompose_core.py",
    "scripts/sprite_decompose_manifest.py",
    "scripts/sprite_decompose.py",
    "scripts/test_sprite_decompose.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "evals/evals.json",
    "evals/trigger-evals.json",
    "evals/files/tiny-atlas.ppm",
    "evals/files/tiny-regions.json",
    "skill-card.prompt.md",
    "skill-card.png",
)
REQUIRED_EVAL_TAGS = frozenset({"smoke", "edge", "negative", "disclosure", "verification", "process"})


@dataclass(frozen=True, slots=True)
class ValidationReport:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    checked_files: int
    eval_count: int

    @property
    def valid(self) -> bool:
        return not self.errors


def validate_skill(skill_path: str | Path) -> ValidationReport:
    root = Path(skill_path).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    if root.name != "sprite-decompose":
        errors.append("skill directory must be named sprite-decompose")

    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            errors.append(f"missing regular file: {relative}")

    skill_path_resolved = root / "SKILL.md"
    if skill_path_resolved.is_file():
        _validate_skill_md(skill_path_resolved, errors)
    _validate_python(root, errors)
    _validate_json_files(root, errors)
    eval_count = _validate_evals(root, errors)
    _validate_triggers(root, errors)
    _validate_template(root, errors)
    _validate_fixture(root, errors)
    _validate_card(root, errors)
    _validate_portability(root, errors)
    _validate_thin_wrappers(root, errors, warnings)
    return ValidationReport(tuple(errors), tuple(warnings), len(REQUIRED_FILES), eval_count)


def _validate_skill_md(path: Path, errors: list[str]) -> None:
    content = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(?P<frontmatter>.*?)\n---\n(?P<body>.*)\Z", content, re.DOTALL)
    if match is None:
        errors.append("SKILL.md must contain closed YAML frontmatter")
        return
    frontmatter = match.group("frontmatter")
    name_match = re.search(r'^name:\s*["\']?([^"\'\n]+)["\']?\s*$', frontmatter, re.MULTILINE)
    description_match = re.search(r'^description:\s*"([^"]+)"\s*$', frontmatter, re.MULTILINE)
    if name_match is None or name_match.group(1) != "sprite-decompose":
        errors.append("SKILL.md frontmatter name must match the directory")
    if description_match is None:
        errors.append("SKILL.md must have a quoted one-line description")
    else:
        description = description_match.group(1)
        if len(description) > 450:
            errors.append(f"SKILL.md description is {len(description)} chars; maximum is 450")
        for phrase in ("sprite sheets", "transparent PNG", "manifest"):
            if phrase not in description:
                errors.append(f"SKILL.md description must include {phrase!r}")
    body_lines = match.group("body").count("\n") + 1
    if body_lines > 500:
        errors.append(f"SKILL.md body has {body_lines} lines; maximum is 500")
    for required in (
        "references/region-review.md",
        "templates/regions.example.json",
        "scripts/sprite_decompose.py",
        "--overwrite",
        "overlapping or occluded",
    ):
        if required not in content:
            errors.append(f"SKILL.md must retain load-bearing contract: {required}")


def _validate_python(root: Path, errors: list[str]) -> None:
    for path in sorted((root / "scripts").glob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as error:
            errors.append(f"Python syntax error in {path.relative_to(root)}: {error}")


def _validate_json_files(root: Path, errors: list[str]) -> None:
    for relative in (
        "metadata.json",
        "pyrightconfig.json",
        "templates/regions.example.json",
        "evals/evals.json",
        "evals/trigger-evals.json",
        "evals/files/tiny-regions.json",
    ):
        path = root / relative
        if not path.is_file():
            continue
        try:
            cast(object, json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError as error:
            errors.append(f"invalid JSON in {relative}: {error}")


def _validate_evals(root: Path, errors: list[str]) -> int:
    path = root / "evals" / "evals.json"
    if not path.is_file():
        return 0
    data = _object(_load_json(path), "evals root", errors)
    if data is None:
        return 0
    if data.get("skill_name") != "sprite-decompose":
        errors.append("evals/evals.json skill_name must be sprite-decompose")
    raw_evals = _array(data.get("evals"), "evals", errors)
    if raw_evals is None:
        return 0
    seen_ids: set[int] = set()
    seen_tags: set[str] = set()
    for index, raw_eval in enumerate(raw_evals):
        item = _object(raw_eval, f"evals[{index}]", errors)
        if item is None:
            continue
        identifier = item.get("id")
        if isinstance(identifier, bool) or not isinstance(identifier, int):
            errors.append(f"evals[{index}].id must be an integer")
        elif identifier in seen_ids:
            errors.append(f"duplicate eval id: {identifier}")
        else:
            seen_ids.add(identifier)
        for field in ("name", "prompt", "expected_output"):
            if not isinstance(item.get(field), str) or not cast(str, item[field]).strip():
                errors.append(f"evals[{index}].{field} must be a non-empty string")
        assertions = _array(item.get("assertions"), f"evals[{index}].assertions", errors)
        if not assertions:
            errors.append(f"evals[{index}] must contain typed assertions")
        else:
            for assertion_index, raw_assertion in enumerate(assertions):
                assertion = _object(raw_assertion, f"evals[{index}].assertions[{assertion_index}]", errors)
                if assertion is None:
                    continue
                if not isinstance(assertion.get("text"), str) or not isinstance(assertion.get("type"), str):
                    errors.append(f"evals[{index}].assertions[{assertion_index}] needs text and type strings")
        tags = _array(item.get("tags", []), f"evals[{index}].tags", errors) or []
        for tag in tags:
            if isinstance(tag, str):
                seen_tags.add(tag)
            else:
                errors.append(f"evals[{index}] contains a non-string tag")
        files = _array(item.get("files", []), f"evals[{index}].files", errors) or []
        for raw_file in files:
            if not isinstance(raw_file, str):
                errors.append(f"evals[{index}] contains a non-string fixture path")
                continue
            fixture = (root / raw_file).resolve()
            try:
                fixture.relative_to(root)
            except ValueError:
                errors.append(f"eval fixture escapes package: {raw_file}")
            if not fixture.is_file():
                errors.append(f"missing eval fixture: {raw_file}")
    missing_tags = sorted(REQUIRED_EVAL_TAGS - seen_tags)
    if missing_tags:
        errors.append(f"missing eval tag coverage: {', '.join(missing_tags)}")
    return len(raw_evals)


def _validate_triggers(root: Path, errors: list[str]) -> None:
    path = root / "evals" / "trigger-evals.json"
    if not path.is_file():
        return
    raw = _load_json(path)
    values = _array(raw, "trigger eval root", errors)
    if values is None:
        return
    positive = 0
    negative = 0
    for index, value in enumerate(values):
        item = _object(value, f"trigger[{index}]", errors)
        if item is None:
            continue
        if set(item) != {"query", "should_trigger"}:
            errors.append(f"trigger[{index}] must contain only query and should_trigger")
        if not isinstance(item.get("query"), str) or not cast(str, item["query"]).strip():
            errors.append(f"trigger[{index}].query must be a non-empty string")
        should_trigger = item.get("should_trigger")
        if not isinstance(should_trigger, bool):
            errors.append(f"trigger[{index}].should_trigger must be boolean")
        elif should_trigger:
            positive += 1
        else:
            negative += 1
    if positive < 2 or negative < 3:
        errors.append("trigger evals require direct and implicit positives plus at least three adjacent negatives")


def _validate_template(root: Path, errors: list[str]) -> None:
    path = root / "templates" / "regions.example.json"
    if not path.is_file():
        return
    try:
        load_spec(path, 256, 128)
    except SpecError as error:
        errors.append(f"region template does not parse against its example canvas: {error}")


def _validate_fixture(root: Path, errors: list[str]) -> None:
    image_path = root / "evals" / "files" / "tiny-atlas.ppm"
    spec_path = root / "evals" / "files" / "tiny-regions.json"
    if not image_path.is_file() or not spec_path.is_file():
        return
    try:
        with Image.open(image_path) as image:
            if image.size != (16, 10):
                errors.append(f"tiny fixture must be 16x10, got {image.size}")
            load_spec(spec_path, image.width, image.height)
    except (OSError, UnidentifiedImageError, SpecError) as error:
        errors.append(f"fixture contract failed: {error}")


def _validate_card(root: Path, errors: list[str]) -> None:
    path = root / "skill-card.png"
    if not path.is_file():
        return
    if path.stat().st_size < 10_000:
        errors.append("skill-card.png is suspiciously small")
    try:
        with Image.open(path) as image:
            if image.size != (1024, 576) or image.format != "PNG":
                errors.append("skill-card.png must be a 1024x576 PNG")
    except (OSError, UnidentifiedImageError) as error:
        errors.append(f"cannot read skill-card.png: {error}")


def _validate_portability(root: Path, errors: list[str]) -> None:
    text_suffixes = {".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
    macos_home_marker = "/" + "Users" + "/"
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in text_suffixes:
            continue
        text = path.read_text(encoding="utf-8")
        if macos_home_marker in text:
            errors.append(f"machine-specific evidence leaked into {path.relative_to(root)}")


def _validate_thin_wrappers(root: Path, errors: list[str], warnings: list[str]) -> None:
    for relative, maximum in (("README.md", 60), ("AGENTS.md", 40)):
        path = root / relative
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").count("\n") + 1
        if lines > maximum:
            errors.append(f"{relative} is not a thin wrapper: {lines} lines > {maximum}")
    if (root / "references" / "region-review.md").is_file():
        lines = (root / "references" / "region-review.md").read_text(encoding="utf-8").count("\n") + 1
        if lines > 300:
            warnings.append("references/region-review.md exceeds 300 lines; add navigation if it grows further")


def _load_json(path: Path) -> object:
    return cast(object, json.loads(path.read_text(encoding="utf-8")))


def _object(value: object, label: str, errors: list[str]) -> dict[str, object] | None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be a JSON object")
        return None
    result: dict[str, object] = {}
    for raw_key, raw_value in cast(dict[object, object], value).items():
        if not isinstance(raw_key, str):
            errors.append(f"{label} contains a non-string key")
            return None
        result[raw_key] = raw_value
    return result


def _array(value: object, label: str, errors: list[str]) -> list[object] | None:
    if not isinstance(value, list):
        errors.append(f"{label} must be a JSON array")
        return None
    return list(cast(list[object], value))


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        return 1
    report = validate_skill(arguments[0])
    print(
        json.dumps(
            {
                "valid": report.valid,
                "checked_files": report.checked_files,
                "eval_count": report.eval_count,
                "errors": list(report.errors),
                "warnings": list(report.warnings),
            },
            indent=2,
        )
    )
    return 0 if report.valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
