#!/usr/bin/env python3
"""Regression tests for the generated-file validator."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
from types import ModuleType


def load_validator() -> ModuleType:
    sys.dont_write_bytecode = True
    path = Path(__file__).with_name("validate_agents_md.py")
    spec = importlib.util.spec_from_file_location("validate_agents_md", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


VALID_AGENTS = """# Project Agent Guidance

## Critical boundaries

- Inspect the relevant implementation and tests before editing.
- Do not discard user work; preserve it and keep the change narrowly scoped.
- Do not bypass failed validation; fix the cause or report the blocked check and risk.

## Project shape

- Preserve the separation between domain decisions, orchestration, and external effects.
- Keep domain language consistent with the behavior documented by the project.

## Maintainability

- Prefer readable names, explicit responsibilities, and strong data contracts where supported.
- Avoid speculative abstraction; use the smallest design that preserves the current intent.
- Comment rationale and invariants when structure alone cannot explain them.

## Tests and verification

- Do not leave changed behavior untested; add focused regression evidence or report the gap.
- Keep tests deterministic and assert observable behavior.
- Run the repository's configured checks in proportion to the change.

## Completion

- Report what changed, verification performed, remaining limitations, and meaningful risk.
- Remove stale guidance when the project evolves and prefer automated enforcement for strict invariants.
"""


def write_project(root: Path, agents: str, claude: str = "@AGENTS.md\n") -> None:
    (root / "AGENTS.md").write_text(agents, encoding="utf-8")
    (root / "CLAUDE.md").write_text(claude, encoding="utf-8")
    (root / "pyproject.toml").write_text(
        '[project]\nname = "sample-service"\ndependencies = ["httpx"]\n',
        encoding="utf-8",
    )
    workflow = root / ".github" / "workflows" / "checks.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text("steps:\n  - run: ruff check\n", encoding="utf-8")


def main() -> int:
    validator = load_validator()

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_project(root, VALID_AGENTS)
        result = validator.validate_project(root)
        assert result["valid"], result

        write_project(root, VALID_AGENTS, "# duplicated instructions\n")
        result = validator.validate_project(root)
        assert not result["valid"]
        assert any("exactly @AGENTS.md" in error for error in result["errors"])

        write_project(root, VALID_AGENTS + "\nSee https://example.invalid and run `tool test`.\n")
        result = validator.validate_project(root)
        assert not result["valid"]
        assert any("forbidden URL" in error for error in result["errors"])
        assert any("inline or fenced code" in error for error in result["errors"])

        write_project(root, VALID_AGENTS + "\nUse ./temporary/config at version 4.2.1.\n")
        result = validator.validate_project(root)
        assert not result["valid"]
        assert any("forbidden relative path" in error for error in result["errors"])
        assert any("forbidden version number" in error for error in result["errors"])

        write_project(root, VALID_AGENTS + "\nRun ruff check and use httpx for requests.\n")
        result = validator.validate_project(root)
        assert not result["valid"]
        assert any("package or executable" in error for error in result["errors"])
        assert any("httpx" in error and "ruff" in error for error in result["errors"])

        write_project(root, VALID_AGENTS + "\n" + ("context " * 1300) + "\n")
        result = validator.validate_project(root)
        assert not result["valid"]
        assert any("1200-word release ceiling" in error for error in result["errors"])

    print("validate_agents_md regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
