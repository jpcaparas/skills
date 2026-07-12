#!/usr/bin/env python3
"""Validate generated root agent guidance without judging project semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shlex
from typing import TypedDict

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - fallback for older Python runtimes
    tomllib = None  # type: ignore[assignment]


class ValidationResult(TypedDict):
    valid: bool
    errors: list[str]
    warnings: list[str]
    metrics: dict[str, int]


REQUIRED_CONCEPTS = {
    "inspection before editing": ("inspect", "read", "understand"),
    "narrow scope": ("scope", "smallest", "narrow"),
    "maintainability": ("maintain", "readable", "responsibil", "smallest coherent", "abstraction", "comment"),
    "tests": ("test", "regression"),
    "verification": ("verify", "validation", "check"),
    "honest handoff": ("risk", "limitation", "blocked", "not verified", "report"),
}

FORBIDDEN_PATTERNS = {
    "URL": re.compile(r"(?:https?://|www\.)", re.IGNORECASE),
    "absolute path": re.compile(r"(?:^|[\s(])(?:/[^\s]+|[A-Za-z]:[\\/][^\s]+|~[/\\][^\s]+)"),
    "relative path": re.compile(r"(?:^|[\s(])(?:\.{1,2}[/\\]|[\w.-]+[/\\][\w./\\-]+)"),
    "version number": re.compile(r"\b(?:v(?:ersion)?\s*)?\d+\.\d+(?:\.\d+)?\b", re.IGNORECASE),
    "shell prompt or fenced command": re.compile(r"(?:^|\n)\s*(?:\$\s+|```(?:sh|bash|shell|powershell|cmd)?\s*$)", re.IGNORECASE | re.MULTILINE),
}

IGNORED_PARTS = {
    ".git",
    ".venv",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "__pycache__",
}

COMMAND_SEPARATORS = re.compile(r"(?:&&|\|\||;|\|)")


def first_command_token(command: str) -> str | None:
    """Return a likely executable token from a configured command string."""

    for segment in COMMAND_SEPARATORS.split(command):
        try:
            tokens = shlex.split(segment.strip(), posix=True)
        except ValueError:
            continue
        while tokens and "=" in tokens[0] and not tokens[0].startswith(("-", "=")):
            tokens.pop(0)
        if tokens and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]*", tokens[0]):
            return tokens[0]
    return None


def collect_project_literals(project_root: Path) -> set[str]:
    """Collect dependency and executable names evidenced by project configuration."""

    literals: set[str] = set()
    for path in project_root.rglob("*"):
        if not path.is_file() or any(part in IGNORED_PARTS for part in path.relative_to(project_root).parts):
            continue

        name = path.name.lower()
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        if name == "package.json":
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {}
            for key in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                values = payload.get(key, {})
                if isinstance(values, dict):
                    literals.update(item for item in values if isinstance(item, str))
            scripts = payload.get("scripts", {})
            if isinstance(scripts, dict):
                for command in scripts.values():
                    if isinstance(command, str) and (token := first_command_token(command)):
                        literals.add(token)

        elif name == "pyproject.toml":
            dependency_values: list[str] = []
            if tomllib is not None:
                try:
                    payload = tomllib.loads(text)
                except Exception:
                    payload = {}
                project = payload.get("project", {})
                if isinstance(project, dict):
                    dependencies = project.get("dependencies", [])
                    if isinstance(dependencies, list):
                        dependency_values.extend(item for item in dependencies if isinstance(item, str))
                    optional = project.get("optional-dependencies", {})
                    if isinstance(optional, dict):
                        for group in optional.values():
                            if isinstance(group, list):
                                dependency_values.extend(item for item in group if isinstance(item, str))
                groups = payload.get("dependency-groups", {})
                if isinstance(groups, dict):
                    for group in groups.values():
                        if isinstance(group, list):
                            dependency_values.extend(item for item in group if isinstance(item, str))
            else:
                for block in re.finditer(r"dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL):
                    dependency_values.extend(re.findall(r"[\"']([^\"']+)[\"']", block.group(1)))

            for dependency in dependency_values:
                if match := re.match(r"([A-Za-z][A-Za-z0-9_.-]*)", dependency):
                    literals.add(match.group(1))

        elif name == "cargo.toml":
            in_dependencies = False
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith("["):
                    in_dependencies = "dependencies" in stripped.lower()
                elif in_dependencies and (match := re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=", stripped)):
                    literals.add(match.group(1))

        elif name == "go.mod":
            for match in re.finditer(r"^\s*([A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+)\s+v\d", text, re.MULTILINE):
                literals.add(match.group(1))

        if path.suffix.lower() in {".yml", ".yaml"}:
            for match in re.finditer(r"^\s*(?:-\s*)?run:\s*([^|>\n].*)$", text, re.MULTILINE):
                if token := first_command_token(match.group(1)):
                    literals.add(token)

    return {literal for literal in literals if len(literal) >= 2}


def project_literal_violations(agents: str, literals: set[str]) -> list[str]:
    violations: list[str] = []
    for literal in sorted(literals, key=str.casefold):
        pattern = re.compile(rf"(?<![\w.-]){re.escape(literal)}(?![\w.-])", re.IGNORECASE)
        if pattern.search(agents):
            violations.append(literal)
    return violations


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
        claude = ""
    else:
        claude = claude_path.read_text(encoding="utf-8")
        if claude != "@AGENTS.md\n":
            errors.append("CLAUDE.md must contain exactly @AGENTS.md followed by one newline")

    lines = agents.splitlines()
    words = re.findall(r"\b\w+\b", agents)
    headings = [line for line in lines if line.startswith("#")]
    project_literals = collect_project_literals(project_root)

    if agents and not agents.endswith("\n"):
        errors.append("AGENTS.md must end with a newline")
    if not agents.strip():
        errors.append("AGENTS.md must not be empty")
    if len(lines) > 200:
        errors.append(f"AGENTS.md exceeds the 200-line release ceiling ({len(lines)})")
    elif len(lines) > 160:
        warnings.append(f"AGENTS.md is longer than the preferred compact range ({len(lines)} lines)")
    if len(lines) < 20 and agents:
        warnings.append("AGENTS.md may be too thin to encode project-specific guidance")
    if len(headings) < 3 and agents:
        warnings.append("AGENTS.md may be difficult to scan because it has fewer than three headings")
    if len(words) > 1200:
        errors.append(f"AGENTS.md exceeds the 1200-word release ceiling ({len(words)})")
    elif len(words) > 900:
        warnings.append(f"AGENTS.md is longer than the preferred compact range ({len(words)} words)")

    for label, pattern in FORBIDDEN_PATTERNS.items():
        match = pattern.search(agents)
        if match:
            errors.append(f"AGENTS.md contains a forbidden {label}: {match.group(0).strip()}")

    if "`" in agents:
        errors.append("AGENTS.md contains inline or fenced code; remove literal commands, paths, and tool names")

    literal_violations = project_literal_violations(agents, project_literals)
    if literal_violations:
        errors.append(
            "AGENTS.md contains project package or executable name(s): "
            + ", ".join(literal_violations)
        )

    lowered = agents.lower()
    for label, alternatives in REQUIRED_CONCEPTS.items():
        if not any(term in lowered for term in alternatives):
            errors.append(f"AGENTS.md does not express required concept: {label}")

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
        warnings.append(
            f"{len(unpaired)} negative guardrail(s) may not name the permitted action"
        )

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "agents_lines": len(lines),
            "agents_words": len(words),
            "headings": len(headings),
            "negative_guardrails": len(negative_lines),
            "project_literals_checked": len(project_literals),
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
