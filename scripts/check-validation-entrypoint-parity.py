#!/usr/bin/env python3
"""Ensure local and CI validation entrypoints share one canonical command."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Final, TypeAlias


JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


REPO_ROOT: Final = Path(__file__).resolve().parents[1]
CANONICAL_SCRIPT: Final = "scripts/validate-all-skills.sh"
CANONICAL_COMMAND: Final = f"bash {CANONICAL_SCRIPT}"
STOP_CHECK_SCRIPT: Final = "scripts/agent-stop-checks.sh"


def read_text(relative_path: str) -> str:
    """Read one repository file using a stable UTF-8 boundary."""
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def load_json_object(relative_path: str, errors: list[str]) -> JsonObject | None:
    """Parse a repository JSON object at the untyped file boundary."""
    try:
        parsed: JsonValue = json.loads(read_text(relative_path))
    except json.JSONDecodeError as exc:
        errors.append(f"{relative_path} contains invalid JSON: {exc}")
        return None

    if not isinstance(parsed, dict):
        errors.append(f"{relative_path} must contain a JSON object")
        return None
    return parsed


def validate_package_script(errors: list[str]) -> None:
    """Require the package-level validation alias to call the canonical script."""
    package = load_json_object("package.json", errors)
    if package is None:
        return

    scripts = package.get("scripts")
    if not isinstance(scripts, dict) or scripts.get("validate") != CANONICAL_COMMAND:
        errors.append(
            f"package.json scripts.validate must equal {CANONICAL_COMMAND!r}"
        )


def validate_workflow(errors: list[str]) -> None:
    """Require GitHub Actions to invoke the canonical script directly."""
    workflow = read_text(".github/workflows/validate-skills.yml")
    expected = f"run: {CANONICAL_COMMAND}"
    if expected not in workflow:
        errors.append(f"GitHub Actions must contain {expected!r}")


def validate_pre_push(errors: list[str]) -> None:
    """Require pre-push to run the full package validator, not a subset."""
    pre_push = read_text(".husky/pre-push")
    if " run validate\n" not in pre_push:
        errors.append(".husky/pre-push must run the full 'validate' package script")
    if "validate:readme" in pre_push:
        errors.append(".husky/pre-push must not use the README-only validation subset")


def validate_stop_pipeline(errors: list[str]) -> None:
    """Require every agent stop adapter to route through shared stop checks."""
    stop_checks = read_text(STOP_CHECK_SCRIPT)
    invocation = f'bash "$REPO_ROOT/{CANONICAL_SCRIPT}"'
    if invocation not in stop_checks:
        errors.append(f"{STOP_CHECK_SCRIPT} must invoke the canonical validator")

    for harness in ("claude", "codex", "devin"):
        config_path = f"hooks/stop/{harness}.json"
        config = load_json_object(config_path, errors)
        if config is None:
            continue

        scripts = config.get("scripts")
        if not isinstance(scripts, list):
            errors.append(f"{config_path} must contain a scripts list")
            continue

        paths = {
            item.get("path")
            for item in scripts
            if isinstance(item, dict) and isinstance(item.get("path"), str)
        }
        if STOP_CHECK_SCRIPT not in paths:
            errors.append(f"{config_path} must invoke {STOP_CHECK_SCRIPT}")


def main() -> int:
    """Report every parity violation in one actionable failure."""
    errors: list[str] = []
    validate_package_script(errors)
    validate_workflow(errors)
    validate_pre_push(errors)
    validate_stop_pipeline(errors)

    if errors:
        print("Validation entrypoint parity check failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(
        "Validation entrypoints are aligned: GitHub Actions, Husky pre-push, "
        "and agent stop hooks use the canonical validator."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
