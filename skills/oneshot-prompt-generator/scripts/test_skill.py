#!/usr/bin/env python3
"""Run deterministic semantic checks for oneshot-prompt-generator."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from validate import as_string_mapping, validate_skill


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One named deterministic contract result."""

    name: str
    passed: bool
    evidence: str


Check = Callable[[Path], CheckResult]


def read_json(path: Path) -> object:
    """Read a committed JSON fixture for deterministic contract checks."""

    return json.loads(path.read_text(encoding="utf-8"))


def check_branch_routing(root: Path) -> CheckResult:
    """Every source branch must be directly reachable from SKILL.md."""

    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    required = (
        "references/live-interfaces.md",
        "references/still-visuals.md",
        "references/time-based-media.md",
        "references/documents-and-code.md",
    )
    missing = [path for path in required if path not in skill]
    return CheckResult(
        name="routes every source branch directly",
        passed=not missing,
        evidence=(
            "all four branch references are present"
            if not missing
            else "missing " + ", ".join(missing)
        ),
    )


def check_output_boundary(root: Path) -> CheckResult:
    """The canonical contract must stop after a copy-ready prompt."""

    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    required = (
        "Return only the raw paste-ready prompt",
        "do not wrap the prompt in a code fence",
        "Do not append the evidence ledger",
        "Do not build, render, dispatch a worker",
    )
    missing = [phrase for phrase in required if phrase not in skill]
    return CheckResult(
        name="keeps the handoff prompt-only",
        passed=not missing,
        evidence=(
            "raw output and no-implementation boundaries are explicit"
            if not missing
            else "missing " + ", ".join(missing)
        ),
    )


def check_target_precedence(root: Path) -> CheckResult:
    """Default web behavior and explicit target override both need evals."""

    raw = read_json(root / "evals" / "evals.json")
    mapping = as_string_mapping(raw)
    evals = mapping.get("evals") if mapping is not None else None
    names = {
        item["name"]
        for raw_item in evals
        if isinstance(evals, list)
        and (item := as_string_mapping(raw_item)) is not None
        and isinstance(item.get("name"), str)
    }
    required = {
        "website-reference-defaults-to-web-app",
        "document-defaults-to-web-product",
        "explicit-native-mobile-target-overrides-default",
        "mixed-evidence-user-constraints-win",
    }
    missing = sorted(required - names)
    return CheckResult(
        name="tests target default and override precedence",
        passed=not missing,
        evidence=(
            "default and explicit-target cases are declared"
            if not missing
            else "missing " + ", ".join(missing)
        ),
    )


def check_adversarial_evidence(root: Path) -> CheckResult:
    """Prompt injection must be represented in both fixture and grading."""

    fixture = (root / "evals" / "files" / "prompt-injection-source.md").read_text(
        encoding="utf-8"
    )
    eval_text = (root / "evals" / "evals.json").read_text(encoding="utf-8")
    passed = (
        "SYSTEM OVERRIDE" in fixture
        and "source-prompt-injection-is-treated-as-data" in eval_text
        and "No local file is uploaded" in eval_text
    )
    return CheckResult(
        name="tests source prompt injection as untrusted data",
        passed=passed,
        evidence=(
            "malicious fixture and no-effect assertions are present"
            if passed
            else "malicious fixture or safety assertion is missing"
        ),
    )


def check_secondary_state_fixture(root: Path) -> CheckResult:
    """The website fixture must expose more than a static happy path."""

    html = (
        root / "evals" / "files" / "reference-site" / "index.html"
    ).read_text(encoding="utf-8")
    script = (
        root / "evals" / "files" / "reference-site" / "app.js"
    ).read_text(encoding="utf-8")
    styles = (
        root / "evals" / "files" / "reference-site" / "styles.css"
    ).read_text(encoding="utf-8")
    required = (
        "empty-state",
        "form-error",
        "form-success",
        "showModal",
        'event.key === "Escape"',
        "prefers-reduced-motion",
    )
    combined = html + script + styles
    missing = [fragment for fragment in required if fragment not in combined]
    return CheckResult(
        name="website fixture exposes secondary states",
        passed=not missing,
        evidence=(
            "empty, error, success, dialog, Escape, and reduced-motion states exist"
            if not missing
            else "missing " + ", ".join(missing)
        ),
    )


def check_trigger_boundaries(root: Path) -> CheckResult:
    """Invocation corpus must contain each closest competing workflow."""

    raw = read_json(root / "evals" / "trigger-evals.json")
    queries = [
        query
        for item in raw
        if isinstance(raw, list)
        and (mapping := as_string_mapping(item)) is not None
        and mapping.get("should_trigger") is False
        and isinstance((query := mapping.get("query")), str)
    ]
    joined = "\n".join(queries).lower()
    required_fragments = (
        "build this screenshot",
        "one-shot website experiments",
        "unstyled semantic html",
        "name of the floating panel",
        "summarize this book",
        "tweet",
        "generate the finished",
    )
    missing = [fragment for fragment in required_fragments if fragment not in joined]
    return CheckResult(
        name="covers adjacent near-miss owners",
        passed=not missing,
        evidence=(
            "implementation, execution, markup, naming, notes, social replica, and "
            "image-generation near misses are present"
            if not missing
            else "missing " + ", ".join(missing)
        ),
    )


def check_branch_disclosure(root: Path) -> CheckResult:
    """Each conditional route needs positive and negative disclosure coverage."""

    raw = read_json(root / "evals" / "evals.json")
    mapping = as_string_mapping(raw)
    eval_values = mapping.get("evals") if mapping is not None else None
    disclosures: list[str] = []
    if isinstance(eval_values, list):
        for raw_eval in eval_values:
            eval_item = as_string_mapping(raw_eval)
            assertions = eval_item.get("assertions") if eval_item is not None else None
            if not isinstance(assertions, list):
                continue
            for raw_assertion in assertions:
                assertion = as_string_mapping(raw_assertion)
                if (
                    assertion is not None
                    and assertion.get("type") == "disclosure"
                    and isinstance(assertion.get("text"), str)
                ):
                    disclosures.append(assertion["text"].lower())

    references = (
        "references/live-interfaces.md",
        "references/still-visuals.md",
        "references/time-based-media.md",
        "references/documents-and-code.md",
    )
    missing_routes: list[str] = []
    for selected in references:
        unrelated = [path for path in references if path != selected]
        if not any(
            selected in disclosure
            and "no read" in disclosure
            and all(path in disclosure for path in unrelated)
            for disclosure in disclosures
        ):
            missing_routes.append(selected)

    return CheckResult(
        name="declares selective disclosure evidence",
        passed=not missing_routes,
        evidence=(
            "every single-source branch requires its reference and excludes all "
            "unrelated branches"
            if not missing_routes
            else "missing complete positive/negative coverage for "
            + ", ".join(missing_routes)
        ),
    )


def run_checks(root: Path) -> list[CheckResult]:
    """Run semantic checks in stable, human-readable order."""

    checks: tuple[Check, ...] = (
        check_branch_routing,
        check_output_boundary,
        check_target_precedence,
        check_adversarial_evidence,
        check_secondary_state_fixture,
        check_trigger_boundaries,
        check_branch_disclosure,
    )
    return [check(root) for check in checks]


def main(argv: list[str]) -> int:
    """CLI entrypoint."""

    if len(argv) > 2:
        print("Usage: test_skill.py [skill-path]", file=sys.stderr)
        return 2
    root = Path(argv[1] if len(argv) == 2 else ".").resolve()

    validation = validate_skill(root)
    if not validation.valid:
        print("FAIL package validation:", file=sys.stderr)
        for error in validation.errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    results = run_checks(root)
    for result in results:
        state = "PASS" if result.passed else "FAIL"
        print(f"{state}: {result.name} — {result.evidence}")

    failed = [result for result in results if not result.passed]
    if failed:
        print(f"FAIL: {len(failed)} semantic checks failed.", file=sys.stderr)
        return 1

    print(f"PASS: all {len(results)} semantic checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
