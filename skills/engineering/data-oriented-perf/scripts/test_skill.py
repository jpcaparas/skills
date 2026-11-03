#!/usr/bin/env python3
"""
Run packaging checks for the data-oriented-perf skill, including the verbatim
source-quote and passive-trigger contracts that a reword would silently break.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import validate


REQUIRED_TAGS = {"smoke", "edge", "negative", "disclosure", "passive"}

# Jarred Sumner, https://x.com/jarredsumner/status/2117037940031496252
SOURCE_PROMPTS = (
    "how do we rewrite this to better leverage data-oriented design principles",
    "can you replace those hash tables with a flat array? can we make the pointers "
    "an index into the array? can we pack the most commonly used data into upper "
    "bits of the index?",
    "caching is cope for a slow design. do not add caches and delete all existing "
    "caches. instead, redesign it to be faster",
    "should this be a structure of arrays instead of an array of structures?",
)
SOURCE_URL = "https://x.com/jarredsumner/status/2117037940031496252"

REQUIRED_SECTIONS = (
    "## Passive Trigger",
    "## The Four Prompts",
    "## Authority Boundaries",
    "## Decision Tree",
    "## Quick Reference",
    "## When Not to Apply",
)


def fail(results: dict[str, Any], message: str) -> None:
    results["errors"].append(message)
    results["passed"] = False


def blockquotes(text: str) -> list[str]:
    return [line[2:].strip() for line in text.splitlines() if line.startswith("> ")]


def check_source_contract(root: Path, results: dict[str, Any]) -> None:
    skill_text = (root / "SKILL.md").read_text(encoding="utf-8")
    notes_text = (root / "references" / "source-notes.md").read_text(encoding="utf-8")

    skill_quotes = blockquotes(skill_text)
    if skill_quotes != list(SOURCE_PROMPTS):
        fail(
            results,
            "SKILL.md block quotes must be exactly the four source prompts, verbatim and in order",
        )
    for prompt in SOURCE_PROMPTS:
        if f"> {prompt}" not in notes_text:
            fail(results, f"references/source-notes.md is missing verbatim prompt: {prompt[:40]}...")

    for label, text in (("SKILL.md", skill_text), ("source-notes.md", notes_text)):
        if "Jarred Sumner" not in text:
            fail(results, f"{label} must attribute Jarred Sumner")
    if SOURCE_URL not in notes_text:
        fail(results, "references/source-notes.md must cite the source post URL")

    for heading in REQUIRED_SECTIONS:
        if not re.search(rf"^{re.escape(heading)}$", skill_text, re.MULTILINE):
            fail(results, f"SKILL.md is missing section: {heading}")


def check_evals(root: Path, results: dict[str, Any]) -> None:
    data = json.loads((root / "evals" / "evals.json").read_text(encoding="utf-8"))
    evals = data.get("evals", [])
    results["tests_found"] = len(evals)
    seen_tags: set[str] = set()
    seen_ids: set[int] = set()

    for index, item in enumerate(evals):
        label = item.get("name", f"eval-{index}")
        for field in ("id", "name", "prompt", "expected_output", "assertions"):
            if field not in item:
                fail(results, f"eval '{label}' missing required field: {field}")
        if item.get("id") in seen_ids:
            fail(results, f"eval '{label}' reuses id {item.get('id')}")
        seen_ids.add(item.get("id"))
        seen_tags.update(item.get("tags", []))
        for assertion in item.get("assertions", []):
            if not (isinstance(assertion, dict) and assertion.get("text")):
                fail(results, f"eval '{label}' has an invalid assertion")
        for rel_path in item.get("files", []):
            if not (root / rel_path).exists():
                fail(results, f"eval '{label}' references missing file: {rel_path}")

    for tag in sorted(REQUIRED_TAGS - seen_tags):
        fail(results, f"missing eval coverage for tag: {tag}")

    triggers = json.loads((root / "evals" / "trigger-evals.json").read_text(encoding="utf-8"))
    if not isinstance(triggers, list) or not triggers:
        fail(results, "evals/trigger-evals.json must be a non-empty list")
        return
    outcomes = {item.get("should_trigger") for item in triggers if isinstance(item, dict)}
    if outcomes != {True, False}:
        fail(results, "trigger evals must include both positive and negative queries")
    results["trigger_evals"] = len(triggers)


def run_tests(skill_path: str) -> dict[str, Any]:
    root = Path(skill_path).resolve()
    results: dict[str, Any] = {
        "skill_name": root.name,
        "tests_found": 0,
        "trigger_evals": 0,
        "errors": [],
        "warnings": [],
        "passed": True,
    }

    validation = validate.validate_skill(str(root))
    results["warnings"].extend(validation["warnings"])
    if not validation["valid"]:
        for error in validation["errors"]:
            fail(results, error)
        return results

    check_source_contract(root, results)
    check_evals(root, results)
    return results


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python3 test_skill.py <skill-path>", file=sys.stderr)
        return 1

    results = run_tests(sys.argv[1])
    print(f"Skill: {results['skill_name']}")
    print(f"Evals found: {results['tests_found']}")
    print(f"Trigger evals found: {results['trigger_evals']}")
    for warning in results["warnings"]:
        print(f"  WARN: {warning}")
    for error in results["errors"]:
        print(f"  ERROR: {error}")
    print("\nPASS: all checks passed" if results["passed"] else "\nFAIL: one or more checks failed")
    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
