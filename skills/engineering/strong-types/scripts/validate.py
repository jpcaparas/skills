#!/usr/bin/env python3
"""Validate the strong-types skill package."""

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
    "references/php.md",
    "references/typescript.md",
    "references/python.md",
    "references/jvm-and-dotnet.md",
    "references/go-rust-swift.md",
    "references/gradual-languages.md",
    "references/review-rubric.md",
    "references/gotchas.md",
    "references/source-notes.md",
    "scripts/analyze_type_strictness.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "templates/type-review.md",
    "evals/evals.json",
]
REQUIRED_SKILL_TERMS = [
    "Passive Trigger",
    "strict_types",
    "mixed",
    "unknown",
    "fallback",
    "nullable",
    "enum",
    "DTO",
    "exhaustive",
    "parse, don't validate",
    "generics",
    "do not force the issue",
]
REQUIRED_SOURCE_URLS = [
    "https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/",
    "https://www.php.net/manual/en/language.types.declarations.php",
    "https://phpstan.org/user-guide/rule-levels",
    "https://phpstan.org/user-guide/baseline",
    "https://www.typescriptlang.org/tsconfig/#strict",
    "https://mypy.readthedocs.io/en/stable/existing_code.html",
    "https://learn.microsoft.com/en-us/dotnet/csharp/nullable-references",
    "https://openjdk.org/jeps/409",
    "https://kotlinlang.org/docs/null-safety.html",
    "https://go.dev/blog/intro-generics",
    "https://doc.rust-lang.org/book/ch06-00-enums.html",
    "https://sorbet.org/docs/overview",
    "https://hexdocs.pm/elixir/typespecs.html",
]
REQUIRED_EVAL_TAGS = {
    "smoke",
    "edge",
    "negative",
    "disclosure",
    "php",
    "typescript",
    "python",
    "review",
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
        for phrase in REQUIRED_SKILL_TERMS:
            if phrase.lower() not in content.lower():
                errors.append(f"SKILL.md must cover concept: {phrase}")
        if "{{ skill:maintainable-code }}" not in content:
            errors.append("SKILL.md must use symbolic reference to {{ skill:maintainable-code }}")
        if "?? $location->banner" not in content:
            errors.append("SKILL.md must show the canonical fallback-chain offense and its typed fix")
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
            if line_count > 300 and "## Table of Contents" not in text:
                errors.append(f"large reference without TOC: {path.relative_to(root)}")
            if line_count > 1000:
                warnings.append(f"large reference file: {path.relative_to(root)}")
            for ref in extract_references(text):
                if not (path.parent / ref).exists() and not (root / ref).exists():
                    errors.append(f"{path.relative_to(root)} reference does not exist: {ref}")

    source_notes = root / "references" / "source-notes.md"
    if source_notes.is_file():
        source_text = read_text(source_notes)
        for url in REQUIRED_SOURCE_URLS:
            if url not in source_text:
                errors.append(f"references/source-notes.md missing source URL: {url}")

    gradual = root / "references" / "gradual-languages.md"
    if gradual.is_file():
        gradual_text = read_text(gradual).lower()
        for phrase in ["do not force", "over-enforcement", "jsdoc", "sorbet"]:
            if phrase not in gradual_text:
                errors.append(f"references/gradual-languages.md must cover: {phrase}")

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
