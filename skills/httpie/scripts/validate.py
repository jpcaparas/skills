#!/usr/bin/env python3
"""
validate.py - Validate the httpie skill structure and conventions.

Usage:
    python3 validate.py <skill-path>
"""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, str]:
    if not content.startswith("---"):
        return None, content

    end = content.find("---", 3)
    if end == -1:
        return None, content

    frontmatter_text = content[3:end].strip()
    body = content[end + 3 :].strip()
    data: dict[str, str] = {}

    for line in frontmatter_text.splitlines():
        if not line.strip() or line.startswith((" ", "\t", "#")):
            continue
        match = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$", line)
        if not match:
            continue
        key = match.group(1)
        value = match.group(2).strip()
        if value[:1] in {'"', "'"} and value[-1:] == value[:1]:
            value = value[1:-1]
        data[key] = value

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


def has_toc_heading(content: str) -> bool:
    patterns = [
        r"^#+\s+table\s+of\s+contents",
        r"^#+\s+toc\b",
        r"^#+\s+contents\b",
        r"^\-\s+\[.*\]\(#",
    ]
    for line in content.splitlines():
        stripped = line.strip().lower()
        if any(re.match(pattern, stripped) for pattern in patterns):
            return True
    return False


def syntax_check_python(path: Path) -> str | None:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return str(exc)
    return None


def syntax_check_shell(path: Path) -> str | None:
    proc = subprocess.run(
        ["sh", "-n", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        return proc.stderr.strip() or "shell syntax check failed"
    return None


def validate_skill(skill_path: str) -> dict[str, object]:
    root = Path(skill_path).resolve()
    errors: list[str] = []
    warnings: list[str] = []
    metrics = {"skill_md_lines": 0, "reference_count": 0, "total_lines": 0}

    skill_md = root / "SKILL.md"
    if not skill_md.is_file():
        return {"valid": False, "errors": ["SKILL.md does not exist"], "warnings": warnings, "metrics": metrics}

    content = skill_md.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(content)
    metrics["skill_md_lines"] = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    metrics["total_lines"] = metrics["skill_md_lines"]

    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter")
    else:
        if frontmatter.get("name") != root.name:
            errors.append("Frontmatter name does not match directory name")
        if not frontmatter.get("description"):
            errors.append("Frontmatter missing description")

    body_lines = body.count("\n") + (1 if body and not body.endswith("\n") else 0)
    if body_lines > 500:
        warnings.append("SKILL.md body exceeds 500 lines target")

    required_dirs = ["references", "scripts", "templates", "evals", "assets", "agents"]
    for directory in required_dirs:
        if not (root / directory).is_dir():
            errors.append(f"Missing directory: {directory}/")

    required_files = [
        "README.md",
        "AGENTS.md",
        "metadata.json",
        "agents/openai.yaml",
        "references/commands.md",
        "references/transient.md",
        "references/configuration.md",
        "references/patterns.md",
        "references/gotchas.md",
        "scripts/probe_httpie.py",
        "scripts/validate.py",
        "scripts/test_skill.py",
        "templates/httpie-fallback.sh",
        "evals/evals.json",
        "assets/.gitkeep",
    ]
    for rel_path in required_files:
        if not (root / rel_path).exists():
            errors.append(f"Missing required file: {rel_path}")

    for rel_path in extract_file_references(content):
        if not (root / rel_path).exists():
            errors.append(f"Referenced file does not exist: {rel_path}")

    for rel_path in ["scripts/probe_httpie.py", "scripts/validate.py", "scripts/test_skill.py"]:
        script_path = root / rel_path
        if script_path.is_file():
            syntax_error = syntax_check_python(script_path)
            if syntax_error:
                errors.append(f"Python syntax error in {rel_path}: {syntax_error}")

    template_path = root / "templates" / "httpie-fallback.sh"
    if template_path.is_file():
        shell_error = syntax_check_shell(template_path)
        if shell_error:
            errors.append(f"Shell syntax error in templates/httpie-fallback.sh: {shell_error}")

    metadata_path = root / "metadata.json"
    if metadata_path.is_file():
        try:
            json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"metadata.json is not valid JSON: {exc}")

    refs_root = root / "references"
    if refs_root.is_dir():
        for ref_path in refs_root.rglob("*.md"):
            ref_content = ref_path.read_text(encoding="utf-8")
            lines = ref_content.count("\n") + (1 if ref_content and not ref_content.endswith("\n") else 0)
            metrics["reference_count"] += 1
            metrics["total_lines"] += lines
            if lines > 1000:
                errors.append(f"Reference file exceeds 1000 lines: {ref_path.relative_to(root)}")
            elif lines > 300 and not has_toc_heading(ref_content):
                warnings.append(f"Reference file >300 lines without TOC: {ref_path.relative_to(root)}")
            for rel_path in extract_file_references(ref_content):
                if not (root / rel_path).exists():
                    errors.append(f"Referenced file does not exist: {rel_path}")

    evals_path = root / "evals" / "evals.json"
    if evals_path.is_file():
        try:
            evals_data = json.loads(evals_path.read_text(encoding="utf-8"))
            evals = evals_data.get("evals", [])
            tags = {tag for item in evals for tag in item.get("tags", [])}
            for tag in ["smoke", "edge", "negative", "disclosure"]:
                if tag not in tags:
                    errors.append(f"Missing eval coverage for tag: {tag}")
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is not valid JSON: {exc}")

    return {"valid": not errors, "errors": errors, "warnings": warnings, "metrics": metrics}


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        raise SystemExit(1)

    result = validate_skill(sys.argv[1])
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
