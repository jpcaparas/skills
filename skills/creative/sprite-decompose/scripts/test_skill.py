#!/usr/bin/env python3
"""Run package preflight and deterministic fixture evidence."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import validate


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def run_command(command: list[str], cwd: Path) -> CheckResult:
    completed = subprocess.run(command, cwd=cwd, check=False, text=True, capture_output=True)
    detail = completed.stdout.strip() or completed.stderr.strip()
    return CheckResult(" ".join(command[1:3]), completed.returncode == 0, detail)


def run_fixture(root: Path) -> CheckResult:
    script = root / "scripts" / "sprite_decompose.py"
    source = root / "evals" / "files" / "tiny-atlas.ppm"
    regions = root / "evals" / "files" / "tiny-regions.json"
    with tempfile.TemporaryDirectory(prefix="sprite-decompose-package-fixture-") as temporary:
        output = Path(temporary) / "output"
        extract = subprocess.run(
            [sys.executable, str(script), "extract", str(source), str(regions), str(output)],
            cwd=root,
            check=False,
            text=True,
            capture_output=True,
        )
        if extract.returncode != 0:
            return CheckResult("fixture extraction", False, extract.stderr.strip() or extract.stdout.strip())
        verify = subprocess.run(
            [sys.executable, str(script), "verify", str(output)],
            cwd=root,
            check=False,
            text=True,
            capture_output=True,
        )
        expected = {"red-token.png", "sprite-002.png", "manifest.json"}
        actual = {path.name for path in output.iterdir()}
        if verify.returncode != 0:
            return CheckResult("fixture extraction", False, verify.stderr.strip() or verify.stdout.strip())
        if actual != expected:
            return CheckResult("fixture extraction", False, f"expected {sorted(expected)}, found {sorted(actual)}")
        raw: object = cast(object, json.loads((output / "manifest.json").read_text(encoding="utf-8")))
        if not isinstance(raw, dict) or cast(dict[str, object], raw).get("sprite_count") != 2:
            return CheckResult("fixture extraction", False, "manifest sprite_count is not 2")
        return CheckResult("fixture extraction", True, verify.stdout.strip())


def run_tests(skill_path: str | Path) -> tuple[CheckResult, ...]:
    root = Path(skill_path).resolve()
    report = validate.validate_skill(root)
    validation = CheckResult(
        "package validation",
        report.valid,
        f"{report.checked_files} files, {report.eval_count} evals; errors={list(report.errors)}",
    )
    unit = run_command(
        [sys.executable, str(root / "scripts" / "test_sprite_decompose.py")],
        root,
    )
    fixture = run_fixture(root)
    return validation, unit, fixture


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1
    results = run_tests(arguments[0])
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status}: {result.name}")
        if result.detail:
            print(f"  {result.detail}")
    passed = all(result.passed for result in results)
    print("\nPASS: all package checks passed" if passed else "\nFAIL: one or more package checks failed")
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
