#!/usr/bin/env python3
"""Validate the maintainable-code skill package."""

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
    "references/decomposition.md",
    "references/commenting.md",
    "references/review-rubric.md",
    "references/implementation-plans.md",
    "references/gotchas.md",
    "references/source-notes.md",
    "scripts/analyze_maintainability.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
    "templates/maintainability-review.md",
    "evals/evals.json",
]

COMMENTING_REQUIRED_TERMS = {
    "GitHub Actions/YAML/Shell": ["GitHub Actions", "YAML", "shell", "gh api", "jq"],
    "TypeScript/JavaScript": ["TypeScript", "JavaScript", "```ts"],
    "Python": ["Python", "```py"],
    "Go": ["Go", "```go"],
    "Rust": ["Rust", "```rust"],
    "Java/Kotlin/C#": ["Java", "Kotlin", "C#", "```java", "```kotlin", "```csharp"],
    "SQL": ["SQL", "```sql"],
    "HTML/CSS": ["HTML", "CSS", "```html", "```css"],
    "Infrastructure config": ["Terraform", "Kubernetes", "```hcl"],
}

OFFICIAL_SOURCE_URLS = [
    "https://www.php.net/manual/en/language.basic-syntax.comments.php",
    "https://docs.python.org/3/tutorial/controlflow.html#documentation-strings",
    "https://laravel.com/docs/13.x/eloquent-mutators",
    "https://laravel.com/docs/13.x/routing",
    "https://nextjs.org/docs/app/api-reference/file-conventions/route",
    "https://nextjs.org/docs/app/getting-started/fetching-data",
]


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
        if "references/commenting.md" not in content:
            errors.append("SKILL.md must route dense or operational code to references/commenting.md")
        review_section = re.search(r"- Reviewing code:[\s\S]*?(?=\n- |\n## )", content)
        if not review_section or "references/commenting.md" not in review_section.group(0):
            errors.append("SKILL.md reviewing route must mention references/commenting.md for operational code")
        plan_section = re.search(r"- Writing a plan[\s\S]*?(?=\n- |\n## )", content)
        if not plan_section or "references/commenting.md" not in plan_section.group(0):
            errors.append("SKILL.md planning route must mention references/commenting.md for operational code")
        maintainer_context = re.search(r"future maintainer|junior maintainer|next maintainer", content, re.IGNORECASE)
        system_context = re.search(r"fundamentals|system history|system context|session context", content, re.IGNORECASE)
        if not maintainer_context or not system_context:
            errors.append("SKILL.md must state the future maintainer assumption")
        if metrics["skill_md_lines"] > 500:
            warnings.append("SKILL.md exceeds 500 lines")
        for ref in extract_references(content):
            if not (root / ref).exists():
                errors.append(f"SKILL.md reference does not exist: {ref}")

    refs_dir = root / "references"
    if refs_dir.is_dir():
        for path in refs_dir.rglob("*.md"):
            metrics["reference_count"] += 1
            line_count = len(read_text(path).splitlines())
            metrics["total_lines"] += line_count
            if line_count > 1000 and "## Table of Contents" not in read_text(path):
                warnings.append(f"large reference without TOC: {path.relative_to(root)}")

    commenting_path = root / "references" / "commenting.md"
    if commenting_path.is_file():
        commenting = read_text(commenting_path)
        if "## Table of Contents" not in commenting:
            errors.append("references/commenting.md must include a table of contents")
        if "line count" not in commenting:
            errors.append("references/commenting.md must say maintainability beats line-count reduction")
        if commenting.count("Weak:") < 5 or commenting.count("Better:") < 5:
            errors.append("references/commenting.md must include multiple weak/better examples")
        for scope_term in ["class", "method", "property", "block"]:
            if not re.search(scope_term, commenting, re.IGNORECASE):
                errors.append(f"references/commenting.md must cover {scope_term}-level comments")
        if "junior" not in commenting.lower() or "bullet" not in commenting.lower() or "numbered" not in commenting.lower():
            errors.append("references/commenting.md must include junior-friendly structured comment guidance")
        ascii_terms = ["ASCII", "diagram", "stale", "conflict", "prose"]
        missing_ascii_terms = [term for term in ascii_terms if term.lower() not in commenting.lower()]
        if missing_ascii_terms:
            errors.append(
                "references/commenting.md missing ASCII diagram guardrail terms: "
                + ", ".join(missing_ascii_terms)
            )
        if "->" not in commenting or "+-->" not in commenting:
            errors.append("references/commenting.md must include an ASCII flow diagram example")
        if "official documentation" not in commenting.lower() and "official source" not in commenting.lower():
            errors.append("references/commenting.md must require official sources for framework/language claims")
        for url in OFFICIAL_SOURCE_URLS:
            if url not in commenting:
                errors.append(f"references/commenting.md missing verified official source URL: {url}")
        for label, terms in COMMENTING_REQUIRED_TERMS.items():
            missing = [term for term in terms if term not in commenting]
            if missing:
                errors.append(f"references/commenting.md missing {label} coverage: {', '.join(missing)}")

    evals_path = root / "evals" / "evals.json"
    if evals_path.is_file():
        try:
            evals = json.loads(read_text(evals_path))
        except json.JSONDecodeError as exc:
            errors.append(f"evals/evals.json is invalid JSON: {exc}")
        else:
            if evals.get("skill_name") != root.name:
                errors.append("evals skill_name must match directory name")
            if not evals.get("evals"):
                errors.append("evals/evals.json must contain at least one eval")
            all_tags = {
                tag
                for item in evals.get("evals", [])
                for tag in item.get("tags", [])
            }
            if "comments" not in all_tags:
                errors.append("evals/evals.json must cover developer-comment guidance")
            if "markup" not in all_tags:
                errors.append("evals/evals.json must cover markup/config comment guidance")
            if "sources" not in all_tags:
                errors.append("evals/evals.json must cover official-source guidance")
            if "diagrams" not in all_tags:
                errors.append("evals/evals.json must cover ASCII diagram guidance")

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
