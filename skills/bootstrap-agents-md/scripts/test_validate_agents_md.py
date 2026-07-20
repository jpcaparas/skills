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


VALID_AGENTS = """# Ledgerbird

- Payout intent is immutable after external acceptance.
- Replayed intent keys return the recorded result without another dispatch.
- Run `uv run pytest` and `ruff check src tests` before handoff.
- Use `docs/payout-lifecycle.md` when changing acceptance or cancellation policy.
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

        # Stable commands and repository-relative references are valid context.
        write_project(root, VALID_AGENTS)
        result = validator.validate_project(root)
        assert result["valid"], result

        write_project(root, VALID_AGENTS, "# duplicated instructions\n")
        result = validator.validate_project(root)
        assert not result["valid"]
        assert any("exactly @AGENTS.md" in error for error in result["errors"])

        # Literal dependencies, versions, and maintained URLs are not structural defects.
        write_project(
            root,
            VALID_AGENTS
            + "\nCompatibility requires httpx 0.27; see https://example.invalid/contract.\n",
        )
        result = validator.validate_project(root)
        assert result["valid"], result

        # A possible machine-local path is a review signal because explicit user contracts may allow it.
        write_project(root, VALID_AGENTS + "\nLocal evidence was found at /opt/company/project.\n")
        result = validator.validate_project(root)
        assert result["valid"], result
        assert any("machine-local absolute path" in warning for warning in result["warnings"])

        # Small projects are allowed to produce genuinely small guidance.
        write_project(root, "# Pocketcalc\n\nPreserve signed zero in formatted output.\n")
        result = validator.validate_project(root)
        assert result["valid"], result

        write_project(root, VALID_AGENTS + "\n" + ("context " * 1300) + "\n")
        result = validator.validate_project(root)
        assert not result["valid"]
        assert any("1200-word release ceiling" in error for error in result["errors"])

    print("validate_agents_md regression tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
