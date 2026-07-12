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


@dataclass(frozen=True)
class ValidationState:
    root: Path
    errors: list[str]
    warnings: list[str]
    metrics: dict[str, int]


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    if not content.startswith("---"):
        return None, content
    end = content.find("---", 3)
    if end == -1:
        return None, content
    data: dict[str, str] = {}
    for line in content[3:end].strip().splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)$", line)
        if not match:
            continue
        value = match.group(2).strip()
        data[match.group(1)] = value[1:-1] if value[:1] in {"'", '"'} and value[-1:] == value[:1] else value
    return data, content[end + 3 :].strip()


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


def validate_evals(path: Path, state: ValidationState) -> None:
    """Validate the portable eval schema rather than merely parsing its JSON."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        state.errors.append(f"evals/evals.json is not valid JSON: {exc}")
        return
    if not isinstance(payload, dict) or not isinstance(payload.get("skill_name"), str):
        state.errors.append("evals/evals.json must contain a string skill_name")
        return
    evals = payload.get("evals")
    if not isinstance(evals, list) or not evals:
        state.errors.append("evals/evals.json must contain a non-empty evals list")
        return
    tags: set[str] = set()
    for index, item in enumerate(evals):
        location = f"evals[{index}]"
        if not isinstance(item, dict):
            state.errors.append(f"{location} must be an object")
            continue
        for key in ("name", "prompt", "expected_output", "assertions", "tags"):
            if key not in item:
                state.errors.append(f"{location} is missing {key}")
        if not isinstance(item.get("name"), str) or not isinstance(item.get("prompt"), str):
            state.errors.append(f"{location} name and prompt must be strings")
        if not isinstance(item.get("expected_output"), str):
            state.errors.append(f"{location} expected_output must be a string")
        assertions = item.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            state.errors.append(f"{location} assertions must be a non-empty list")
        else:
            for assertion_index, assertion in enumerate(assertions):
                if not isinstance(assertion, dict) or not isinstance(assertion.get("text"), str) or not assertion["text"]:
                    state.errors.append(f"{location}.assertions[{assertion_index}] must have non-empty text")
        item_tags = item.get("tags")
        if not isinstance(item_tags, list) or not all(isinstance(tag, str) and tag for tag in item_tags):
            state.errors.append(f"{location} tags must be a list of non-empty strings")
        else:
            tags.update(item_tags)
        files = item.get("files", [])
        if not isinstance(files, list) or not all(isinstance(file, str) and file for file in files):
            state.errors.append(f"{location} files must be a list of non-empty strings when present")
        else:
            for file in files:
                if not (state.root / file).exists():
                    state.errors.append(f"{location} references missing file: {file}")
    for tag in ("smoke", "edge", "negative", "disclosure"):
        if tag not in tags:
            state.errors.append(f"Missing eval coverage for tag: {tag}")
    state.metrics["eval_count"] = len(evals)


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


def validate_skill(skill_path: str) -> dict[str, object]:
    root = Path(skill_path).resolve()
    state = ValidationState(root=root, errors=[], warnings=[], metrics={"skill_md_lines": 0, "reference_count": 0, "total_lines": 0})
    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        return {"valid": False, "errors": ["SKILL.md does not exist"], "warnings": [], "metrics": state.metrics}
    content = skill_md.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    state.metrics["skill_md_lines"] = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    state.metrics["total_lines"] = state.metrics["skill_md_lines"]
    if frontmatter is None:
        state.errors.append("SKILL.md has no YAML frontmatter")
    elif frontmatter.get("name") != root.name:
        state.errors.append("Frontmatter name does not match directory name")
    elif not frontmatter.get("description"):
        state.errors.append("Frontmatter missing description")
    if body.count("\n") + 1 > 500:
        state.warnings.append("SKILL.md body exceeds 500 lines target")
    for directory in ("references", "scripts", "templates", "evals", "assets", "agents"):
        if not (root / directory).is_dir():
            state.errors.append(f"Missing directory: {directory}/")
    required_files = (
        "README.md", "AGENTS.md", "metadata.json", "agents/openai.yaml",
        "scripts/probe_better_writing.py", "scripts/scan_aiisms.py", "scripts/validate.py", "scripts/test_skill.py",
        "assets/aiisms.json", "evals/evals.json",
    )
    for relative in required_files:
        if not (root / relative).is_file():
            state.errors.append(f"Missing required file: {relative}")
    for relative in extract_file_references(content):
        if not (root / relative).exists():
            state.errors.append(f"Referenced file does not exist: {relative}")
    for relative in ("scripts/probe_better_writing.py", "scripts/scan_aiisms.py", "scripts/validate.py", "scripts/test_skill.py"):
        path = root / relative
        if path.is_file() and (error := syntax_error(path)):
            state.errors.append(f"Python syntax error in {relative}: {error}")
    metadata = root / "metadata.json"
    if metadata.is_file():
        try:
            json.loads(metadata.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            state.errors.append(f"metadata.json is not valid JSON: {exc}")
    references = root / "references"
    if references.is_dir():
        for reference in references.rglob("*.md"):
            reference_content = reference.read_text(encoding="utf-8")
            lines = reference_content.count("\n") + (1 if reference_content and not reference_content.endswith("\n") else 0)
            state.metrics["reference_count"] += 1
            state.metrics["total_lines"] += lines
            if lines > 1000:
                state.errors.append(f"Reference file exceeds 1000 lines: {reference.relative_to(root)}")
            for relative in extract_file_references(reference_content):
                if not (root / relative).exists():
                    state.errors.append(f"Referenced file does not exist: {relative}")
    evals_path = root / "evals" / "evals.json"
    if evals_path.is_file():
        validate_evals(evals_path, state)
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
