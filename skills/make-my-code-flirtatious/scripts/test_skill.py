#!/usr/bin/env python3
"""Run focused validator regressions for make-my-code-flirtatious."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate


Mutation = Callable[[Path], None]


@dataclass(frozen=True, slots=True)
class RegressionCase:
    name: str
    mutate: Mutation
    expected_error: str


def replace_text(path: Path, old: str, new: str, count: int = -1) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"test fixture text not found in {path}: {old}")
    path.write_text(text.replace(old, new, count), encoding="utf-8")


def remove_fidelity_priority(root: Path) -> None:
    replace_text(root / "SKILL.md", "Technical truth outranks the mood", "The mood leads the explanation")


def remove_code_only_target(root: Path) -> None:
    replace_text(root / "SKILL.md", "Flirt with the code, not the user", "Flirt freely with the user")


def remove_high_stakes_restraint(root: Path) -> None:
    replace_text(root / "SKILL.md", "high-stakes code, restrain the style", "high-stakes code, intensify the style")


def erase_negative_triggers(root: Path) -> None:
    replace_text(root / "evals" / "trigger-evals.json", '"should_trigger": false', '"should_trigger": true')


def corrupt_assertion_type(root: Path) -> None:
    replace_text(root / "evals" / "evals.json", '"type": "functional"', '"type": "subjective"', count=1)


REGRESSION_CASES = (
    RegressionCase(
        name="requires technical fidelity",
        mutate=remove_fidelity_priority,
        expected_error="technical-fidelity priority",
    ),
    RegressionCase(
        name="keeps flirtation aimed at code",
        mutate=remove_code_only_target,
        expected_error="code-only flirtation target",
    ),
    RegressionCase(
        name="requires high-stakes restraint",
        mutate=remove_high_stakes_restraint,
        expected_error="high-stakes restraint",
    ),
    RegressionCase(
        name="requires positive and negative trigger coverage",
        mutate=erase_negative_triggers,
        expected_error="at least five positive and five negative",
    ),
    RegressionCase(
        name="rejects unknown assertion types",
        mutate=corrupt_assertion_type,
        expected_error="invalid assertion type",
    ),
)


def run_case(source: Path, case: RegressionCase) -> tuple[bool, str]:
    with tempfile.TemporaryDirectory(prefix="make-my-code-flirtatious-test-") as temporary:
        candidate = Path(temporary) / source.name
        shutil.copytree(source, candidate)
        case.mutate(candidate)
        result = validate.validate_skill(candidate)
        if result.valid:
            return False, f"{case.name}: mutated package unexpectedly passed"
        if not any(case.expected_error in error for error in result.errors):
            return False, f"{case.name}: expected diagnostic not found"
        return True, f"{case.name}: expected diagnostic observed"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: test_skill.py <skill-path>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    package = validate.validate_skill(root)
    checks = [
        (
            package.valid,
            "release package validates" if package.valid else "release package failed: " + "; ".join(package.errors),
        )
    ]
    checks.extend(run_case(root, case) for case in REGRESSION_CASES)

    for passed, message in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {message}")
    passed_count = sum(passed for passed, _ in checks)
    print(f"\n{passed_count}/{len(checks)} focused checks passed")
    return 0 if passed_count == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
