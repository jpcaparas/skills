#!/usr/bin/env python3
"""Validate the lean-text-scaffolding skill structure and rules."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


REQUIRED_DIRS = ["references", "scripts", "templates", "evals", "assets", "agents"]
REQUIRED_FILES = [
    "README.md",
    "AGENTS.md",
    "metadata.json",
    "agents/openai.yaml",
    "references/rules.md",
    "references/research.md",
    "scripts/audit_lean_text.ts",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "templates/.gitkeep",
    "assets/.gitkeep",
    "evals/evals.json",
]
REQUIRED_EVAL_TAGS = {"smoke", "edge", "negative", "disclosure"}


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    if not content.startswith("---"):
        return None, content
    end = content.find("---", 3)
    if end == -1:
        return None, content

    raw = content[3:end].strip()
    body = content[end + 3 :].strip()
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if line.startswith((" ", "\t")) or not line.strip() or line.strip().startswith("#"):
            continue
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$", line)
        if not match:
            continue
        value = match.group(2).strip()
        if value[:1] in {"'", '"'} and value[-1:] == value[:1]:
            value = value[1:-1]
        data[match.group(1)] = value
    return data, body


def extract_file_references(content: str) -> list[str]:
    refs: set[str] = set()
    stripped = re.sub(r"```[\s\S]*?```", "", content)
    placeholder_re = re.compile(r"[{}<>]|/X\.md$|\s")

    for match in re.finditer(r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`", stripped):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.add(path)

    for match in re.finditer(r"\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)", stripped):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.add(path)

    return sorted(refs)


def line_count(text: str) -> int:
    return text.count("\n") + (1 if text and not text.endswith("\n") else 0)


def syntax_check_python(path: Path) -> str | None:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return str(exc)
    return None


def validate_evals(root: Path, errors: list[str]) -> None:
    evals_path = root / "evals" / "evals.json"
    try:
        data = json.loads(evals_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"evals/evals.json is not valid JSON: {exc}")
        return

    if data.get("skill_name") != root.name:
        errors.append("evals/evals.json skill_name does not match directory name")

    evals = data.get("evals", [])
    if not isinstance(evals, list) or not evals:
        errors.append("evals/evals.json must contain at least one eval")
        return

    tags: set[str] = set()
    ids: set[int] = set()
    for item in evals:
        if not isinstance(item, dict):
            errors.append("Each eval must be an object")
            continue
        for field in ["id", "name", "prompt", "expected_output"]:
            if field not in item:
                errors.append(f"Eval missing required field: {field}")
        if isinstance(item.get("id"), int):
            if item["id"] in ids:
                errors.append(f"Duplicate eval id: {item['id']}")
            ids.add(item["id"])
        for tag in item.get("tags", []):
            tags.add(str(tag))
        for assertion in item.get("assertions", []):
            if not isinstance(assertion, dict) or "text" not in assertion or "type" not in assertion:
                errors.append(f"Invalid assertion in eval: {item.get('name', item.get('id', 'unknown'))}")

    missing = sorted(REQUIRED_EVAL_TAGS - tags)
    if missing:
        errors.append("Missing eval coverage for tags: " + ", ".join(missing))


def validate_skill(skill_path: str | Path) -> dict[str, object]:
    root = Path(skill_path).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        return {"valid": False, "errors": ["SKILL.md does not exist"], "warnings": warnings, "metrics": metrics}

    content = skill_md.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    metrics["skill_md_lines"] = line_count(content)
    metrics["total_lines"] = metrics["skill_md_lines"]

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        if frontmatter.get("name") != root.name:
            errors.append("Frontmatter name does not match directory name")
        description = frontmatter.get("description", "")
        if not description:
            errors.append("Frontmatter missing description")
        elif len(description) > 1024:
            errors.append("Frontmatter description exceeds 1024 characters")
        for token in ["web pages", "placeholder", "labels", "explicitly requested"]:
            if token not in description:
                errors.append(f"Frontmatter description must mention '{token}'")

    if line_count(body) > 500:
        warnings.append("SKILL.md body exceeds 500 lines")

    for directory in REQUIRED_DIRS:
        if not (root / directory).is_dir():
            errors.append(f"Missing directory: {directory}/")

    for rel_path in REQUIRED_FILES:
        if not (root / rel_path).exists():
            errors.append(f"Missing required file: {rel_path}")

    all_markdown = [root / "SKILL.md"]
    all_markdown.extend((root / "references").glob("*.md"))
    for path in all_markdown:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(root)
        if "TODO:" in text or "TBD" in text:
            errors.append(f"Leftover placeholder marker in {rel}")
        if path.name == "SKILL.md" and "form labels" not in text:
            errors.append("SKILL.md must explicitly preserve form labels")
        for ref in extract_file_references(text):
            if not (root / ref).exists():
                errors.append(f"Referenced file does not exist: {ref}")
        if path.parent.name == "references":
            metrics["reference_count"] += 1
            metrics["total_lines"] += line_count(text)
            if line_count(text) > 1000:
                errors.append(f"Reference file exceeds 1000 lines: {rel}")

    for rel_path in ["scripts/validate.py", "scripts/test_skill.py"]:
        script = root / rel_path
        if script.exists():
            syntax_error = syntax_check_python(script)
            if syntax_error:
                errors.append(f"Python syntax error in {rel_path}: {syntax_error}")

    ts_script = root / "scripts" / "audit_lean_text.ts"
    if ts_script.exists():
        ts_text = ts_script.read_text(encoding="utf-8")
        if "interface Issue" not in ts_text or "interface AuditReport" not in ts_text:
            errors.append("scripts/audit_lean_text.ts must keep typed report interfaces")
        if re.search(r"\bany\b", ts_text):
            errors.append("scripts/audit_lean_text.ts should avoid TypeScript any")

    metadata_path = root / "metadata.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not metadata.get("references"):
            errors.append("metadata.json must list research references")
    except json.JSONDecodeError as exc:
        errors.append(f"metadata.json is not valid JSON: {exc}")

    if (root / "evals" / "evals.json").exists():
        validate_evals(root, errors)

    return {"valid": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        return 1
    result = validate_skill(sys.argv[1])
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
