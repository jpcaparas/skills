#!/usr/bin/env python3
"""
validate.py — Validate a skill's structure and conventions.

Usage:
    python3 validate.py <skill-path>

Output:
    JSON with {valid: bool, errors: [], warnings: [], metrics: {...}}

Exit codes:
    0 = valid (may have warnings)
    1 = invalid (has errors)
"""

from __future__ import annotations

import json
import os
import re
import sys


def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return None, content

    end = content.find("---", 3)
    if end == -1:
        return None, content

    frontmatter_text = content[3:end].strip()
    body = content[end + 3:].strip()

    # Simple YAML parser for frontmatter (no PyYAML dependency)
    fm = {}
    current_key = None
    for line in frontmatter_text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Handle top-level key: value
        match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)', line)
        if match and not line.startswith(" ") and not line.startswith("\t"):
            key = match.group(1)
            value = match.group(2).strip()
            # Remove surrounding quotes
            if value and value[0] in ('"', "'") and value[-1] == value[0]:
                value = value[1:-1]
            fm[key] = value
            current_key = key

    return fm, body


def count_lines(filepath: str) -> int:
    """Count lines in a file."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)
    except (OSError, UnicodeDecodeError):
        return 0


def extract_file_references(content: str) -> list[str]:
    """Extract file paths referenced in markdown content.

    Skips paths inside fenced code blocks and paths containing
    placeholders (e.g., {lang}, <skill-path>, X.md used as examples).
    """
    refs = []

    # Strip fenced code blocks to avoid matching example paths
    stripped = re.sub(r'```[\s\S]*?```', '', content)

    # Patterns that indicate an illustrative/placeholder path, not a real reference
    placeholder_re = re.compile(r'[{}<>]|/X\.md$|\s')

    # Match backtick-quoted paths: `references/foo.md`, `scripts/bar.py`
    for match in re.finditer(r'`((?:references|scripts|templates|assets|agents|evals)/[^`]+)`', stripped):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.append(path)

    # Match markdown links to local files
    for match in re.finditer(r'\[.*?\]\(((?:references|scripts|templates|assets|agents|evals)/[^)]+)\)', stripped):
        path = match.group(1)
        if not placeholder_re.search(path):
            refs.append(path)

    return list(set(refs))


def has_toc_heading(content: str) -> bool:
    """Check if content has a heading that looks like a table of contents."""
    toc_patterns = [
        r'^#+\s+table\s+of\s+contents',
        r'^#+\s+toc\b',
        r'^#+\s+contents\b',
        r'^\-\s+\[.*\]\(#',  # Markdown link list with anchor refs
    ]
    for line in content.split("\n"):
        stripped = line.strip().lower()
        for pattern in toc_patterns:
            if re.match(pattern, stripped):
                return True
    return False


def validate_skill(skill_path: str) -> dict:
    """Validate a skill and return results."""
    errors = []
    warnings = []
    metrics = {
        "skill_md_lines": 0,
        "reference_count": 0,
        "total_lines": 0,
    }

    skill_path = os.path.abspath(skill_path)
    dir_name = os.path.basename(skill_path)

    # --- Check SKILL.md exists ---
    skill_md_path = os.path.join(skill_path, "SKILL.md")
    if not os.path.isfile(skill_md_path):
        errors.append("SKILL.md does not exist")
        return {"valid": False, "errors": errors, "warnings": warnings, "metrics": metrics}

    # --- Read and parse SKILL.md ---
    with open(skill_md_path, "r", encoding="utf-8") as f:
        content = f.read()

    skill_md_lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    metrics["skill_md_lines"] = skill_md_lines
    metrics["total_lines"] = skill_md_lines

    frontmatter, body = parse_frontmatter(content)

    # --- Validate frontmatter ---
    if frontmatter is None:
        errors.append("SKILL.md has no YAML frontmatter (must start with ---)")
    else:
        # Check name field
        name = frontmatter.get("name", "")
        if not name:
            errors.append("Frontmatter missing required 'name' field")
        else:
            # Validate name format
            if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', name):
                errors.append(
                    f"name '{name}' is invalid: must be lowercase letters, digits, "
                    f"and hyphens (1-64 chars, must start/end with alphanumeric)"
                )
            elif len(name) > 64:
                errors.append(f"name '{name}' exceeds 64 character limit ({len(name)} chars)")

            # Check name matches directory
            if name != dir_name:
                errors.append(
                    f"name '{name}' does not match directory name '{dir_name}'"
                )

        # Check description field
        description = frontmatter.get("description", "")
        if not description:
            errors.append("Frontmatter missing required 'description' field")
        elif len(description) > 1024:
            errors.append(
                f"description exceeds 1024 chars ({len(description)} chars)"
            )

    # --- Check SKILL.md body length ---
    body_lines = body.count("\n") + (1 if body and not body.endswith("\n") else 0)
    if body_lines > 500:
        warnings.append(
            f"SKILL.md body is {body_lines} lines (target: <500). "
            f"Consider moving content to references."
        )

    # --- Check file references in SKILL.md ---
    refs = extract_file_references(content)
    for ref in refs:
        ref_path = os.path.join(skill_path, ref)
        if not os.path.exists(ref_path):
            errors.append(f"Referenced file does not exist: {ref}")

    # --- Check reference files ---
    refs_dir = os.path.join(skill_path, "references")
    if os.path.isdir(refs_dir):
        for root, dirs, files in os.walk(refs_dir):
            for fname in files:
                if fname == ".gitkeep":
                    continue
                fpath = os.path.join(root, fname)
                lines = count_lines(fpath)
                metrics["reference_count"] += 1
                metrics["total_lines"] += lines

                if lines > 1000:
                    errors.append(
                        f"Reference file exceeds 1000 lines: "
                        f"{os.path.relpath(fpath, skill_path)} ({lines} lines)"
                    )
                elif lines > 300:
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            file_content = f.read()
                        if not has_toc_heading(file_content):
                            warnings.append(
                                f"Reference file >300 lines without TOC: "
                                f"{os.path.relpath(fpath, skill_path)} ({lines} lines)"
                            )
                    except (OSError, UnicodeDecodeError):
                        pass

    # --- Check required directories ---
    required_dirs = ["references", "scripts", "templates", "evals", "assets", "agents"]
    for d in required_dirs:
        dpath = os.path.join(skill_path, d)
        if not os.path.isdir(dpath):
            warnings.append(f"Missing recommended directory: {d}/")
        else:
            # Check for .gitkeep in empty directories
            contents = [f for f in os.listdir(dpath) if f != ".gitkeep"]
            if not contents:
                gitkeep = os.path.join(dpath, ".gitkeep")
                if not os.path.exists(gitkeep):
                    warnings.append(f"Empty directory without .gitkeep: {d}/")

    # --- Check evals/evals.json ---
    evals_path = os.path.join(skill_path, "evals", "evals.json")
    if not os.path.isfile(evals_path):
        warnings.append("evals/evals.json not found (recommended for all production skills)")
    else:
        try:
            with open(evals_path, "r", encoding="utf-8") as f:
                evals_data = json.load(f)
            if not isinstance(evals_data.get("evals"), list):
                warnings.append("evals/evals.json: 'evals' field should be an array")
            elif len(evals_data["evals"]) == 0:
                warnings.append("evals/evals.json: no test cases defined (array is empty)")
        except json.JSONDecodeError as e:
            errors.append(f"evals/evals.json is not valid JSON: {e}")

    # --- Count script lines ---
    scripts_dir = os.path.join(skill_path, "scripts")
    if os.path.isdir(scripts_dir):
        for fname in os.listdir(scripts_dir):
            if fname == ".gitkeep":
                continue
            fpath = os.path.join(scripts_dir, fname)
            if os.path.isfile(fpath):
                metrics["total_lines"] += count_lines(fpath)

    # --- Build result ---
    valid = len(errors) == 0
    result = {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }

    return result


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 validate.py <skill-path>", file=sys.stderr)
        sys.exit(1)

    skill_path = sys.argv[1]

    if not os.path.isdir(skill_path):
        print(f"Error: '{skill_path}' is not a directory", file=sys.stderr)
        sys.exit(1)

    result = validate_skill(skill_path)

    # Print human-readable summary
    name = os.path.basename(os.path.abspath(skill_path))
    status = "VALID" if result["valid"] else "INVALID"

    print(f"\nSkill: {name}")
    print(f"Status: {status}")
    print(f"SKILL.md lines: {result['metrics']['skill_md_lines']}")
    print(f"Reference files: {result['metrics']['reference_count']}")
    print(f"Total lines: {result['metrics']['total_lines']}")

    if result["errors"]:
        print(f"\nErrors ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"  ERROR: {e}")

    if result["warnings"]:
        print(f"\nWarnings ({len(result['warnings'])}):")
        for w in result["warnings"]:
            print(f"  WARN: {w}")

    if result["valid"] and not result["warnings"]:
        print("\nNo issues found.")

    # Print JSON to stdout for machine consumption
    print(f"\n--- JSON ---")
    print(json.dumps(result, indent=2))

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
