#!/usr/bin/env python3
"""Run package validation and focused surface-scanner tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from io import StringIO


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from analyze_ste_surface import (
    TextType,
    analyze_text,
    estimate_word_count,
    read_input,
)
import validate


def finding_codes(text: str, text_type: TextType) -> set[str]:
    return {finding.code for finding in analyze_text(text, text_type).findings}


def test_surface_scanner() -> list[str]:
    errors: list[str] = []

    procedure = (
        "Don't remove the cover; the connector is installed and the technician "
        "is monitoring the very long maintenance operation while the second "
        "technician records all applicable measurements and then closes the panel."
    )
    procedure_codes = finding_codes(procedure, TextType.PROCEDURE)
    expected_procedure = {
        "contraction",
        "semicolon",
        "passive-voice",
        "ing-form",
        "coordinated-action",
        "estimated-word-limit",
    }
    missing_procedure = sorted(expected_procedure - procedure_codes)
    if missing_procedure:
        errors.append(
            "Procedure scanner missed expected candidates: "
            + ", ".join(missing_procedure)
        )

    description = (
        "The unit starts. It monitors pressure. It records temperature. "
        "It sends data. It stores faults. It supplies status. It stops safely."
    )
    description_codes = finding_codes(description, TextType.DESCRIPTION)
    if "paragraph-sentence-limit" not in description_codes:
        errors.append("Description scanner missed the paragraph sentence limit")

    protected = """
The command is below.

```bash
monitoring --is-installed --then
```

Use `being-installed` as the exact label.
"""
    protected_codes = finding_codes(protected, TextType.DESCRIPTION)
    if "passive-voice" in protected_codes or "ing-form" in protected_codes:
        errors.append("Scanner inspected protected code content")

    hard_wrapped = (
        "Before you start the functional test, make sure that the hydraulic system "
        "is fully depressurized and the warning placard is installed\n"
        "at the main control panel for all maintenance personnel."
    )
    hard_wrapped_analysis = analyze_text(hard_wrapped, TextType.PROCEDURE)
    if len(hard_wrapped_analysis.sentences) != 1:
        errors.append("Scanner split one hard-wrapped procedure sentence")
    if "estimated-word-limit" not in {
        finding.code for finding in hard_wrapped_analysis.findings
    }:
        errors.append("Scanner missed the hard-wrapped procedure word limit")
    if hard_wrapped_analysis.sentences and hard_wrapped_analysis.sentences[0].line != 1:
        errors.append("Scanner lost the hard-wrapped sentence start line")

    counting_case = (
        "Install the actuator AB-123 (the left flight-control actuator in the "
        "forward equipment bay) to 25 N·m before the "
        '"SYSTEM READY FOR OPERATION" message comes on.'
    )
    if estimate_word_count(counting_case) != 13:
        errors.append("Scanner changed the scoped special-unit counting behavior")

    return errors


def test_json_contract() -> list[str]:
    errors: list[str] = []
    analysis = analyze_text("Remove the cover.", TextType.PROCEDURE)
    record = analysis.as_record()

    try:
        serialized = json.dumps(record)
        reparsed = json.loads(serialized)
    except (TypeError, json.JSONDecodeError) as exc:
        return [f"Scanner JSON record is not serializable: {exc}"]

    if reparsed.get("schema_version") != 1:
        errors.append("Scanner JSON record has an unexpected schema version")
    if reparsed.get("text_type") != "procedure":
        errors.append("Scanner JSON record has an unexpected text type")
    if reparsed.get("sentence_word_limit") != 20:
        errors.append("Scanner JSON record has an unexpected procedure limit")
    return errors


def test_input_contract() -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "sample.md"
        path.write_text("The component is installed.\n", encoding="utf-8")
        analysis = analyze_text(read_input(str(path)), TextType.DESCRIPTION)
        if not analysis.sentences:
            errors.append("Scanner did not read a UTF-8 fixture")

    original_stdin = sys.stdin
    try:
        sys.stdin = StringIO("Remove the cover.\n")
        if read_input("-") != "Remove the cover.\n":
            errors.append("Scanner did not read standard input")
    finally:
        sys.stdin = original_stdin

    return errors


def run_tests(skill_path: str | Path) -> dict[str, object]:
    root = Path(skill_path).resolve()
    validation = validate.validate_skill(root)
    errors = list(validation.errors)
    errors.extend(test_surface_scanner())
    errors.extend(test_json_contract())
    errors.extend(test_input_contract())

    return {
        "skill_name": root.name,
        "package_valid": validation.valid,
        "focused_checks": 3,
        "errors": errors,
        "warnings": list(validation.warnings),
        "passed": not errors,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 2

    result = run_tests(sys.argv[1])
    print(f"Skill: {result['skill_name']}")
    print(f"Package valid: {result['package_valid']}")
    print(f"Focused scanner checks: {result['focused_checks']}")

    warnings = result["warnings"]
    if isinstance(warnings, list) and warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")

    errors = result["errors"]
    if isinstance(errors, list) and errors:
        print("\nIssues:")
        for error in errors:
            print(f"  - {error}")

    passed = result["passed"] is True
    print("\nPASS: all checks passed" if passed else "\nFAIL: one or more checks failed")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
