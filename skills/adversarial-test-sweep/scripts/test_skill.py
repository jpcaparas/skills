#!/usr/bin/env python3
"""Run independent structural preflight for adversarial-test-sweep.

This checker validates package and eval evidence. It executes only the isolated
committed fixture baseline and held-out probe; it never substitutes for paired
with-skill/baseline prompt runs.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from validate import validate_skill


@dataclass(slots=True)
class PreflightResult:
    """Keep human-readable counters and failures in one explicit result type."""

    skill_name: str
    behavioral_cases: int = 0
    assertions: int = 0
    fixture_cases: int = 0
    negative_disclosures: int = 0
    fixture_contract_verified: bool = False
    trigger_positive: int = 0
    trigger_negative: int = 0
    completion_gates: int = 0
    tag_counts: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """A preflight passes only when every independent check has evidence."""

        return not self.errors


def load_json(path: Path) -> object:
    """Erase json.loads' dynamic return type at the file boundary."""

    return json.loads(path.read_text(encoding="utf-8"))


def collect_evals(root: Path, result: PreflightResult) -> None:
    """Count behavior and invocation evidence without reusing validator state."""

    payload = load_json(root / "evals" / "evals.json")
    if not isinstance(payload, dict) or not isinstance(payload.get("evals"), list):
        result.errors.append("behavioral eval payload is not an object with an evals array")
        return

    cases = payload["evals"]
    result.behavioral_cases = len(cases)
    for case in cases:
        if not isinstance(case, dict):
            result.errors.append("behavioral eval contains a non-object case")
            continue
        assertions = case.get("assertions")
        if isinstance(assertions, list):
            result.assertions += len(assertions)
            for assertion in assertions:
                if not isinstance(assertion, dict):
                    continue
                text = assertion.get("text")
                if (
                    assertion.get("type") == "disclosure"
                    and isinstance(text, str)
                    and text.casefold().startswith("does not load ")
                ):
                    result.negative_disclosures += 1
        files = case.get("files")
        if isinstance(files, list) and files:
            result.fixture_cases += 1
        tags = case.get("tags")
        if isinstance(tags, list):
            for tag in tags:
                if isinstance(tag, str):
                    result.tag_counts[tag] = result.tag_counts.get(tag, 0) + 1

    triggers = load_json(root / "evals" / "trigger-evals.json")
    if not isinstance(triggers, list):
        result.errors.append("trigger eval payload is not an array")
        return
    for trigger in triggers:
        if not isinstance(trigger, dict):
            result.errors.append("trigger eval contains a non-object case")
            continue
        should_trigger = trigger.get("should_trigger")
        if should_trigger is True:
            result.trigger_positive += 1
        elif should_trigger is False:
            result.trigger_negative += 1


def verify_fixture_contract(root: Path, result: PreflightResult) -> None:
    """Prove the committed suite is green while its held-out defect probe fails."""

    fixture = root / "evals" / "fixtures" / "parser-weak-oracle"
    try:
        baseline = subprocess.run(
            [sys.executable, "-m", "unittest", "-v"],
            cwd=fixture,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        probe = subprocess.run(
            [sys.executable, "check_duplicate_header.py"],
            cwd=fixture,
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        result.errors.append(f"could not execute committed eval fixture: {exc}")
        return

    baseline_output = baseline.stdout + baseline.stderr
    probe_output = probe.stdout + probe.stderr
    baseline_is_expected = baseline.returncode == 0 and "Ran 3 tests" in baseline_output
    probe_is_expected = (
        probe.returncode == 1
        and "Ran 1 test" in probe_output
        and "HeaderError not raised" in probe_output
        and "FAILED (failures=1)" in probe_output
    )

    if not baseline_is_expected:
        result.errors.append(
            "committed fixture baseline must pass exactly its three starting tests"
        )
    if not probe_is_expected:
        result.errors.append(
            "held-out fixture probe must fail exactly one test because HeaderError was not raised"
        )
    if baseline_is_expected and probe_is_expected:
        result.fixture_contract_verified = True


def run_preflight(root: Path) -> PreflightResult:
    """Check that the package carries discriminating, balanced release evidence."""

    result = PreflightResult(skill_name=root.name)
    validation = validate_skill(str(root))
    validation_errors = validation.get("errors")
    if isinstance(validation_errors, list):
        result.errors.extend(
            str(error) for error in validation_errors if isinstance(error, str)
        )
    elif validation.get("valid") is not True:
        result.errors.append("validator failed without a structured error list")

    try:
        collect_evals(root, result)
        verify_fixture_contract(root, result)
        skill_content = (root / "SKILL.md").read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result.errors.append(f"preflight could not read package evidence: {exc}")
        return result

    result.completion_gates = skill_content.count("**Complete when:**")
    checks = (
        (result.behavioral_cases >= 8, "requires at least eight behavioral cases"),
        (result.assertions >= 20, "requires at least twenty typed assertions"),
        (result.fixture_cases >= 1, "requires at least one committed behavioral fixture"),
        (
            result.negative_disclosures >= 4,
            "requires a negative loading assertion for every disclosure branch",
        ),
        (
            result.fixture_contract_verified,
            "requires a green fixture baseline with a failing held-out probe",
        ),
        (result.trigger_positive >= 3, "requires at least three positive trigger cases"),
        (result.trigger_negative >= 3, "requires at least three negative trigger cases"),
        (result.completion_gates >= 9, "requires one completion gate per operating phase"),
        (result.tag_counts.get("negative", 0) >= 2, "requires multiple behavioral near-misses"),
        (result.tag_counts.get("disclosure", 0) >= 3, "requires reference-routing evidence"),
        (result.tag_counts.get("safety", 0) >= 2, "requires multiple safety-boundary cases"),
    )
    for passed, message in checks:
        if not passed:
            result.errors.append(message)
    return result


def main(argv: list[str]) -> int:
    """Print a compact report for repository-wide validation."""

    if len(argv) != 1:
        print("Usage: python3 scripts/test_skill.py <skill-path>", file=sys.stderr)
        return 2

    root = Path(argv[0]).expanduser().resolve()
    result = run_preflight(root)
    print(f"Skill: {result.skill_name}")
    print(f"Behavioral cases: {result.behavioral_cases}")
    print(f"Assertions: {result.assertions}")
    print(f"Fixture cases: {result.fixture_cases}")
    print(f"Negative disclosure assertions: {result.negative_disclosures}")
    print(
        "Fixture contract: "
        + ("green baseline / failing probe" if result.fixture_contract_verified else "invalid")
    )
    print(
        "Trigger balance: "
        f"{result.trigger_positive} positive / {result.trigger_negative} negative"
    )
    print(f"Completion gates: {result.completion_gates}")
    for tag, count in sorted(result.tag_counts.items()):
        print(f"  {tag}: {count}")

    if result.errors:
        print("\nIssues:")
        for error in result.errors:
            print(f"  - {error}")
    print("\nPASS: all checks passed" if result.passed else "\nFAIL: one or more checks failed")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
