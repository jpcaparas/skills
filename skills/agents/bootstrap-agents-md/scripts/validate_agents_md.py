#!/usr/bin/env python3
"""Validate generated root agent-guidance structure without judging project semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import TypedDict


class ValidationResult(TypedDict):
    valid: bool
    errors: list[str]
    warnings: list[str]
    metrics: dict[str, int]


MACHINE_LOCAL_ABSOLUTE_PATH = re.compile(
    r"(?:^|[\s(])(?:/(?!/)[^\s)]+|[A-Za-z]:[\\/][^\s)]+|~[/\\][^\s)]+)"
)


def validate_project(project_root: Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    agents_path = project_root / "AGENTS.md"
    claude_path = project_root / "CLAUDE.md"

    if not agents_path.is_file():
        errors.append("missing root AGENTS.md")
        agents = ""
    else:
        agents = agents_path.read_text(encoding="utf-8")

    if not claude_path.is_file():
        errors.append("missing root CLAUDE.md")
    else:
        claude = claude_path.read_text(encoding="utf-8")
        if claude != "@AGENTS.md\n":
            errors.append("CLAUDE.md must contain exactly @AGENTS.md followed by one newline")

    lines = agents.splitlines()
    words = re.findall(r"\b\w+\b", agents)
    headings = [line for line in lines if line.startswith("#")]

    if agents and not agents.endswith("\n"):
        errors.append("AGENTS.md must end with a newline")
    if not agents.strip():
        errors.append("AGENTS.md must not be empty")
    if len(lines) > 200:
        errors.append(f"AGENTS.md exceeds the 200-line release ceiling ({len(lines)})")
    elif len(lines) > 160:
        warnings.append(f"AGENTS.md is longer than the preferred compact range ({len(lines)} lines)")
    if len(words) > 1200:
        errors.append(f"AGENTS.md exceeds the 1200-word release ceiling ({len(words)})")
    elif len(words) > 900:
        warnings.append(f"AGENTS.md is longer than the preferred compact range ({len(words)} words)")

    if match := MACHINE_LOCAL_ABSOLUTE_PATH.search(agents):
        warnings.append(
            "AGENTS.md contains a machine-local absolute path candidate: "
            f"{match.group(0).strip()}"
        )

    negative_lines = [
        line.strip()
        for line in lines
        if re.search(r"\b(?:do not|don't|never|must not|avoid)\b", line, re.IGNORECASE)
    ]
    unpaired = [
        line
        for line in negative_lines
        if not re.search(
            r"\b(?:instead|unless|rather|fix|preserve|report|use|prefer|keep|ask|change|document)\b",
            line,
            re.IGNORECASE,
        )
    ]
    if unpaired:
        warnings.append(f"{len(unpaired)} negative guardrail(s) may not name the permitted action")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "agents_lines": len(lines),
            "agents_words": len(words),
            "headings": len(headings),
            "negative_guardrails": len(negative_lines),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path)
    args = parser.parse_args()
    result = validate_project(args.project_root.resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
