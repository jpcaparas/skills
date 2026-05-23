#!/usr/bin/env python3
"""Validate the oneshot-websites skill package."""

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
    "references/README.md",
    "references/repertoire.md",
    "references/generation-protocol.md",
    "references/catalog-index.md",
    "references/ui-guidance.md",
    "references/quality-bar.md",
    "templates/PROMPT.md",
    "templates/variant-brief.md",
    "templates/manifest.json",
    "templates/catalog-index.html",
    "assets/repertoire.json",
    "agents/variant-worker.md",
    "agents/catalog-curator.md",
    "evals/evals.json",
    "scripts/build_catalog_index.py",
    "scripts/validate_catalog.py",
    "scripts/validate.py",
    "scripts/test_skill.py",
]


def parse_frontmatter(text: str) -> dict:
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    frontmatter: dict[str, str] = {}
    for line in text[3:end].strip().splitlines():
        if ":" not in line or line.startswith(" "):
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] in "'\"" and value[-1] == value[0]:
            value = value[1:-1]
        frontmatter[key.strip()] = value
    return frontmatter


def strip_code_blocks(text: str) -> str:
    return re.sub(r"```[\s\S]*?```", "", text)


def extract_refs(text: str) -> set[str]:
    stripped = strip_code_blocks(text)
    refs: set[str] = set()
    pattern = r"`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`"
    for match in re.finditer(pattern, stripped):
        ref = match.group(1)
        if not re.search(r"[{}<>]|\s", ref):
            refs.add(ref)
    link_pattern = r"\[[^\]]+\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)"
    for match in re.finditer(link_pattern, stripped):
        ref = match.group(1)
        if not re.search(r"[{}<>]|\s", ref):
            refs.add(ref)
    return refs


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        return 1

    root = Path(sys.argv[1]).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 1

    for directory in REQUIRED_DIRS:
        if not (root / directory).is_dir():
            errors.append(f"missing directory: {directory}")

    for file_name in REQUIRED_FILES:
        if not (root / file_name).is_file():
            errors.append(f"missing file: {file_name}")

    skill_md = root / "SKILL.md"
    if skill_md.exists():
        text = skill_md.read_text(encoding="utf-8")
        fm = parse_frontmatter(text)
        if fm.get("name") != root.name:
            errors.append(f"frontmatter name must be {root.name}")
        if not fm.get("description"):
            errors.append("frontmatter description missing")
        elif len(fm["description"]) > 1024:
            errors.append("frontmatter description exceeds 1024 chars")
        if text.count("\n") + 1 > 500:
            warnings.append("SKILL.md is over 500 lines")

    markdown_files = [skill_md] + list((root / "references").glob("*.md"))
    for md_file in markdown_files:
        if not md_file.exists():
            continue
        for ref in extract_refs(md_file.read_text(encoding="utf-8")):
            if not (root / ref).exists():
                errors.append(f"{md_file.relative_to(root)} references missing file: {ref}")

    for json_file in ["metadata.json", "templates/manifest.json", "assets/repertoire.json", "evals/evals.json"]:
        path = root / json_file
        if path.exists():
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"invalid JSON in {json_file}: {exc}")

    repertoire = root / "assets/repertoire.json"
    if repertoire.exists():
        data = json.loads(repertoire.read_text(encoding="utf-8"))
        styles = data.get("styles", [])
        if len(styles) != 11:
            errors.append("assets/repertoire.json must contain 11 styles")
        slugs = [style.get("slug") for style in styles]
        if len(slugs) != len(set(slugs)):
            errors.append("assets/repertoire.json contains duplicate slugs")

    result = {"valid": not errors, "errors": errors, "warnings": warnings}
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
