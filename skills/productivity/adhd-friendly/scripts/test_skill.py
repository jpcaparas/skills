#!/usr/bin/env python3
"""Run focused package and validator-regression tests for adhd-friendly."""

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
    """One package mutation and the diagnostic it must produce."""

    name: str
    mutate: Mutation
    expected_error: str


def replace_text(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"test fixture text not found in {path}: {old}")
    path.write_text(text.replace(old, new), encoding="utf-8")


def break_attribution(root: Path) -> None:
    replace_text(
        root / "metadata.json",
        validate.UPSTREAM_COMMIT,
        "0000000000000000000000000000000000000000",
    )


def remove_notice(root: Path) -> None:
    (root / "THIRD_PARTY_NOTICES.md").unlink()


def erase_positive_triggers(root: Path) -> None:
    replace_text(
        root / "evals" / "trigger-evals.json",
        '"should_trigger": true',
        '"should_trigger": false',
    )


def restore_upstream_overgeneralization(root: Path) -> None:
    skill_path = root / "SKILL.md"
    skill_path.write_text(
        skill_path.read_text(encoding="utf-8") + "\nDopamine is scarce.\n",
        encoding="utf-8",
    )


def remove_implementation_fixture(root: Path) -> None:
    (root / "evals" / "fixtures" / "null-due-date" / "reminder.py").unlink()


REGRESSION_CASES = (
    RegressionCase(
        name="rejects drifted upstream attribution",
        mutate=break_attribution,
        expected_error="metadata attribution field 'source_commit'",
    ),
    RegressionCase(
        name="requires the bundled MIT notice",
        mutate=remove_notice,
        expected_error="missing required file: THIRD_PARTY_NOTICES.md",
    ),
    RegressionCase(
        name="requires positive and negative trigger coverage",
        mutate=erase_positive_triggers,
        expected_error="trigger evals require at least four positive and four negative cases",
    ),
    RegressionCase(
        name="rejects unsupported universal ADHD claims",
        mutate=restore_upstream_overgeneralization,
        expected_error="reintroduces an upstream overgeneralization",
    ),
    RegressionCase(
        name="requires the implementation eval fixture",
        mutate=remove_implementation_fixture,
        expected_error="references a missing file",
    ),
)


def run_regression_case(source_root: Path, case: RegressionCase) -> tuple[bool, str]:
    """Copy the package into an isolated directory and prove a mutation fails."""

    with tempfile.TemporaryDirectory(prefix="adhd-friendly-test-") as temporary:
        candidate = Path(temporary) / source_root.name
        shutil.copytree(source_root, candidate)
        case.mutate(candidate)
        result = validate.validate_skill(candidate)
        matched = any(case.expected_error in error for error in result.errors)
        if result.valid:
            return False, f"{case.name}: mutated package unexpectedly passed"
        if not matched:
            return False, f"{case.name}: expected diagnostic not found"
        return True, f"{case.name}: expected diagnostic observed"


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: test_skill.py <skill-path>", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    package_result = validate.validate_skill(root)
    checks: list[tuple[bool, str]] = [
        (
            package_result.valid,
            "release package validates"
            if package_result.valid
            else "release package failed: " + "; ".join(package_result.errors),
        )
    ]
    checks.extend(run_regression_case(root, case) for case in REGRESSION_CASES)

    for passed, message in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {message}")

    passed_count = sum(passed for passed, _ in checks)
    print(f"\n{passed_count}/{len(checks)} focused checks passed")
    return 0 if passed_count == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
