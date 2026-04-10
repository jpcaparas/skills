#!/usr/bin/env python3
"""
probe_better_writing.py - Lightweight router and self-test for better-writing.

Usage:
    python3 probe_better_writing.py --prompt "..."
    python3 probe_better_writing.py --suite
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass


WRITING_MARKERS = [
    r"\bwrite\b",
    r"\brewrite\b",
    r"\bedit(?:ing)?\b",
    r"\bdraft\b",
    r"\bcopy\b",
    r"\bprose\b",
    r"\bparagraph\b",
    r"\bsentence\b",
    r"\bvoice\b",
    r"\btone\b",
    r"\bclar(?:ity|ify|er)\b",
    r"\btighten\b",
    r"\bessay\b",
    r"\bmemo\b",
    r"\bdocs?\b",
    r"\breadme\b",
    r"\bguide\b",
    r"\btutorial\b",
    r"\bhow-to\b",
    r"\barticle\b",
    r"\blanding page\b",
    r"\bpricing page\b",
    r"\bemail\b",
    r"\bnewsletter\b",
    r"\breport\b",
    r"\brunbook\b",
    r"\bwalkthrough\b",
]


ROUTE_RULES = [
    (
        "foundations",
        [
            r"\bstrunk\b",
            r"\belements? of style\b",
            r"\bconcise\b",
            r"\bclearer\b",
            r"\bclarity\b",
            r"\bcomposition\b",
            r"\bgrammar\b",
            r"\busage\b",
            r"\bbasics?\b",
        ],
        ["references/foundations.md"],
    ),
    (
        "revision-pass-stack",
        [
            r"\bwrite\b",
            r"\brewrite\b",
            r"\bedit(?:ing)?\b",
            r"\btighten\b",
            r"\bpolish\b",
            r"\bcleanup\b",
            r"\brevision\b",
            r"\bdraft\b",
            r"\bimprove\b",
        ],
        ["references/revision-pass-stack.md"],
    ),
    (
        "voice-and-rhythm",
        [
            r"\bstiff\b",
            r"\bflat\b",
            r"\bbloodless\b",
            r"\bformal\b",
            r"\brobotic\b",
            r"\bcadence\b",
            r"\brhythm\b",
            r"\bhedg(?:e|ing)\b",
            r"\bawkward\b",
            r"\bclipped\b",
        ],
        ["references/voice-and-rhythm.md"],
    ),
    (
        "genericity-and-stiffness",
        [
            r"\bgeneric\b",
            r"\bcorporate\b",
            r"\bcanned\b",
            r"\bfluffy\b",
            r"\bbuzzwords?\b",
            r"\bover-signposted\b",
            r"\bdramatic\b",
            r"\bmarketing[- ]speak\b",
            r"\bceremonial\b",
        ],
        ["references/genericity-and-stiffness.md"],
    ),
    (
        "style-bundles",
        [
            r"\bstyle\b",
            r"\btone\b",
            r"\bpublication\b",
            r"\boperator\b",
            r"\bnewsletter\b",
            r"\beditorial\b",
            r"\bessay\b",
            r"\bmemo\b",
            r"\bcopy\b",
            r"\bsimon willison\b",
            r"\bjulia evans\b",
            r"\bgergely\b",
            r"\blenny\b",
            r"\breuters\b",
            r"\bbloomberg\b",
            r"\bpaul graham\b",
        ],
        ["references/style-bundles.md"],
    ),
    (
        "genre-modes",
        [
            r"\bguide\b",
            r"\btutorial\b",
            r"\bhow-to\b",
            r"\bdocs?\b",
            r"\breadme\b",
            r"\brunbook\b",
            r"\bmemo\b",
            r"\bbrief\b",
            r"\breport\b",
            r"\bessay\b",
            r"\barticle\b",
            r"\blanding page\b",
            r"\bhomepage\b",
            r"\bpricing page\b",
            r"\bemail\b",
            r"\bwalkthrough\b",
        ],
        ["references/genre-modes.md"],
    ),
    (
        "gotchas",
        [
            r"\bover-edit(?:ed|ing)?\b",
            r"\bgetting worse\b",
            r"\beach pass\b",
            r"\btoo polished\b",
            r"\bcan'?t get this right\b",
        ],
        ["references/gotchas.md"],
    ),
]


@dataclass(frozen=True)
class TestCase:
    name: str
    prompt: str
    expect: tuple[str, ...]
    forbid: tuple[str, ...] = ()


TEST_CASES = [
    TestCase(
        name="stiff_runbook_intro",
        prompt="Rewrite this runbook intro. It is clearer than before but still stiff and corporate.",
        expect=(
            "references/revision-pass-stack.md",
            "references/voice-and-rhythm.md",
            "references/genericity-and-stiffness.md",
            "references/genre-modes.md",
        ),
    ),
    TestCase(
        name="technical_style_calibration",
        prompt="Help me turn this technical walkthrough into a Simon Willison or Julia Evans style guide without losing precision.",
        expect=(
            "references/style-bundles.md",
            "references/genre-modes.md",
        ),
    ),
    TestCase(
        name="braided_essay_routing",
        prompt="This personal essay probably wants a braided structure and a better ending.",
        expect=(
            "references/style-bundles.md",
            "references/genre-modes.md",
        ),
    ),
    TestCase(
        name="pricing_page_cleanup",
        prompt="Write homepage and pricing page copy for a B2B analytics tool. The current copy is generic.",
        expect=(
            "references/revision-pass-stack.md",
            "references/genericity-and-stiffness.md",
            "references/style-bundles.md",
            "references/genre-modes.md",
        ),
    ),
    TestCase(
        name="non_writing_negative",
        prompt="I am debugging a React hydration error in Next.js.",
        expect=(),
    ),
]


def matches_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def add_unique(items: list[str], new_items: list[str]) -> None:
    for item in new_items:
        if item not in items:
            items.append(item)


def route_prompt(prompt: str) -> list[str]:
    text = prompt.strip().lower()
    if not matches_any(text, WRITING_MARKERS):
        return []

    refs: list[str] = []
    for _, patterns, targets in ROUTE_RULES:
        if matches_any(text, patterns):
            add_unique(refs, targets)

    if refs and "references/revision-pass-stack.md" not in refs:
        if re.search(r"\b(rewrite|edit|tighten|polish|cleanup|improve)\b", text):
            refs.insert(0, "references/revision-pass-stack.md")

    if not refs:
        refs = [
            "references/foundations.md",
            "references/revision-pass-stack.md",
        ]

    return refs


def run_case(case: TestCase) -> dict[str, object]:
    refs = route_prompt(case.prompt)
    missing = [item for item in case.expect if item not in refs]
    forbidden = [item for item in case.forbid if item in refs]
    passed = not missing and not forbidden and (bool(case.expect) or not refs)
    return {
        "name": case.name,
        "passed": passed,
        "expected": list(case.expect),
        "forbidden": list(case.forbid),
        "actual": refs,
        "missing": missing,
        "unexpected": forbidden,
    }


def run_suite() -> dict[str, object]:
    checks = [run_case(case) for case in TEST_CASES]
    passed = all(item["passed"] for item in checks)
    return {
        "passed": passed,
        "checks": checks,
        "summary": {
            "checks_total": len(checks),
            "checks_passed": sum(1 for item in checks if item["passed"]),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Route prompts to better-writing reference files.")
    parser.add_argument("--prompt", help="Prompt to route")
    parser.add_argument("--suite", action="store_true", help="Run the built-in test suite")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format",
    )
    args = parser.parse_args()

    if args.suite:
        result = run_suite()
    elif args.prompt:
        result = {"prompt": args.prompt, "references": route_prompt(args.prompt)}
    else:
        parser.error("pass --prompt or --suite")

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        if args.suite:
            print(
                f"Suite: {result['summary']['checks_passed']}/{result['summary']['checks_total']} passed"
            )
            for check in result["checks"]:
                status = "PASS" if check["passed"] else "FAIL"
                print(f"{status}: {check['name']}")
                if not check["passed"]:
                    print(f"  actual: {check['actual']}")
                    if check["missing"]:
                        print(f"  missing: {check['missing']}")
                    if check["unexpected"]:
                        print(f"  unexpected: {check['unexpected']}")
        else:
            refs = result["references"]
            if refs:
                print("Recommended references:")
                for ref in refs:
                    print(f"- {ref}")
            else:
                print("No writing route detected.")

    return 0 if not args.suite or result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
