#!/usr/bin/env python3
"""Run the better-writing package's portable validation and focused self-tests."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import probe_better_writing
import scan_aiisms
import validate


@dataclass(frozen=True)
class TestSummary:
    package_valid: bool
    probe_passed: bool
    scanner_passed: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return self.package_valid and self.probe_passed and self.scanner_passed and not self.errors


def run_tests(skill_path: str) -> dict[str, object]:
    """Exercise the package without invoking a network or non-standard dependency."""

    root = Path(skill_path).resolve()
    validation = validate.validate_skill(str(root))
    errors = [str(error) for error in validation["errors"]]
    warnings = [str(warning) for warning in validation["warnings"]]
    probe_suite = probe_better_writing.run_suite()
    scanner_suite = scan_aiisms.run_self_tests()
    if not probe_suite["passed"]:
        errors.append("Probe suite failed")
    if not scanner_suite["passed"]:
        errors.append("Scanner self-test failed")
    summary = TestSummary(
        package_valid=bool(validation["valid"]),
        probe_passed=bool(probe_suite["passed"]),
        scanner_passed=bool(scanner_suite["passed"]),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return {
        "skill_name": root.name,
        "passed": summary.passed,
        "package_validation": validation,
        "probe_suite": probe_suite,
        "scanner_suite": scanner_suite,
        "errors": list(summary.errors),
        "warnings": list(summary.warnings),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 1:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1
    result = run_tests(args[0])
    validation = result["package_validation"]
    assert isinstance(validation, dict)
    probe = result["probe_suite"]
    scanner = result["scanner_suite"]
    assert isinstance(probe, dict) and isinstance(scanner, dict)
    print(f"Skill: {result['skill_name']}")
    print(f"Package validation: {'PASS' if validation['valid'] else 'FAIL'}")
    metrics = validation["metrics"]
    assert isinstance(metrics, dict)
    manifest_checks = metrics.get("manifest_checks")
    manifest_checks_passed = metrics.get("manifest_checks_passed")
    assert isinstance(manifest_checks, int) and isinstance(manifest_checks_passed, int)
    print(f"Manifest checks: {manifest_checks_passed}/{manifest_checks} passed")
    eval_schema_checks = metrics.get("eval_schema_checks")
    eval_schema_checks_passed = metrics.get("eval_schema_checks_passed")
    assert isinstance(eval_schema_checks, int) and isinstance(eval_schema_checks_passed, int)
    print(f"Eval schema checks: {eval_schema_checks_passed}/{eval_schema_checks} passed")
    eval_count = metrics.get("eval_count")
    eval_route_checks = metrics.get("eval_route_checks")
    trigger_eval_count = metrics.get("trigger_eval_count")
    trigger_route_checks = metrics.get("trigger_route_checks")
    assert isinstance(eval_count, int) and isinstance(eval_route_checks, int)
    assert isinstance(trigger_eval_count, int) and isinstance(trigger_route_checks, int)
    print(f"Eval route polarity: {eval_route_checks}/{eval_count} matched")
    print(f"Trigger route polarity: {trigger_route_checks}/{trigger_eval_count} matched")
    package_path_checks = metrics.get("package_path_checks")
    package_path_checks_passed = metrics.get("package_path_checks_passed")
    assert isinstance(package_path_checks, int) and isinstance(package_path_checks_passed, int)
    print(f"Package path checks: {package_path_checks_passed}/{package_path_checks} passed")
    print(f"Probe checks: {probe['summary']['checks_passed']}/{probe['summary']['checks_total']} passed")
    scanner_checks = scanner["checks"]
    assert isinstance(scanner_checks, dict)
    print(f"Scanner checks: {sum(1 for passed in scanner_checks.values() if passed)}/{len(scanner_checks)} passed")
    if result["warnings"]:
        print("\nWarnings:")
        for warning in result["warnings"]:
            print(f"- {warning}")
    if result["errors"]:
        print("\nIssues:")
        for error in result["errors"]:
            print(f"- {error}")
    print("\nPASS: all checks passed" if result["passed"] else "\nFAIL: one or more checks failed")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
