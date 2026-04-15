#!/usr/bin/env python3
"""
probe_eli12.py - Small routing probe for the eli12 skill.

Usage:
    python3 probe_eli12.py --prompt "How does auth work?"
    python3 probe_eli12.py --run-suite
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass


POSITIVE_PATTERNS = [
    r"\bhow does\b",
    r"\bwalk me through\b",
    r"\bwhat happens when\b",
    r"\bexplain\b",
    r"\barchitecture\b",
    r"\bsubsystem\b",
    r"\bcodebase\b",
    r"\bmental model\b",
    r"\beli12\b",
    r"\bexplain it simply\b",
    r"\bmake .* easier to understand\b",
]

NEGATIVE_PATTERNS = [
    r"\bfix\b",
    r"\bbug\b",
    r"\bfailing test\b",
    r"\bimplement\b",
    r"\bwrite code\b",
    r"\brefactor\b",
    r"\bcode review\b",
    r"\breview this pr\b",
    r"\bsecurity audit\b",
    r"\boptimi[sz]e\b",
    r"\bchildren'?s story\b",
]

BROAD_PATTERNS = [
    r"\bend-to-end\b",
    r"\bwhat happens when\b",
    r"\barchitecture\b",
    r"\bcodebase\b",
    r"\bsubsystem\b",
    r"\bservice\b",
    r"\bflow\b",
    r"\bpipeline\b",
    r"\brequest\b.*\bresponse\b",
]

NARROW_PATTERNS = [
    r"\bfunction\b",
    r"\bmethod\b",
    r"\bclass\b",
    r"\bhook\b",
    r"\bcomponent\b",
    r"\bhelper\b",
    r"\bfile\b",
    r"\bmiddleware\b",
]


@dataclass
class ProbeResult:
    should_trigger: bool
    mode: str
    reasons: list[str]
    references: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "should_trigger": self.should_trigger,
            "mode": self.mode,
            "reasons": self.reasons,
            "references": self.references,
        }


def _matches_any(patterns: list[str], text: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def analyze_prompt(prompt: str) -> ProbeResult:
    text = prompt.lower().strip()
    reasons: list[str] = []

    if _matches_any(NEGATIVE_PATTERNS, text):
        reasons.append("negative trigger matched")
        return ProbeResult(False, "decline", reasons, [])

    if not _matches_any(POSITIVE_PATTERNS, text):
        reasons.append("no clear explanation trigger detected")
        return ProbeResult(False, "decline", reasons, [])

    references = [
        "references/explainer-prompt.md",
        "references/analogy-patterns.md",
    ]

    if _matches_any(BROAD_PATTERNS, text):
        reasons.append("broad architecture or flow question")
        return ProbeResult(
            True,
            "fanout",
            reasons,
            ["references/explorer-prompt.md", *references],
        )

    if _matches_any(NARROW_PATTERNS, text):
        reasons.append("narrow file or symbol question")
        return ProbeResult(True, "direct", reasons, references)

    reasons.append("general explanation request")
    return ProbeResult(True, "direct", reasons, references)


def run_suite() -> dict[str, object]:
    cases = [
        {
            "name": "broad_architecture",
            "prompt": "Walk me through what happens when a user signs in across this codebase.",
            "expect": {"should_trigger": True, "mode": "fanout"},
        },
        {
            "name": "narrow_function",
            "prompt": "Explain this auth middleware simply.",
            "expect": {"should_trigger": True, "mode": "direct"},
        },
        {
            "name": "negative_bug_fix",
            "prompt": "Fix this failing auth test and tell me why it broke.",
            "expect": {"should_trigger": False, "mode": "decline"},
        },
    ]

    checks: list[dict[str, object]] = []
    for case in cases:
        result = analyze_prompt(case["prompt"]).to_dict()
        passed = (
            result["should_trigger"] == case["expect"]["should_trigger"]
            and result["mode"] == case["expect"]["mode"]
        )
        checks.append(
            {
                "name": case["name"],
                "passed": passed,
                "expected": case["expect"],
                "actual": result,
            }
        )

    summary = {
        "checks_total": len(checks),
        "checks_passed": sum(1 for item in checks if item["passed"]),
    }
    return {"passed": summary["checks_total"] == summary["checks_passed"], "checks": checks, "summary": summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe routing for the eli12 skill.")
    parser.add_argument("--prompt", help="Prompt to classify")
    parser.add_argument("--run-suite", action="store_true", help="Run the built-in probe suite")
    args = parser.parse_args()

    if args.run_suite:
        print(json.dumps(run_suite(), indent=2))
        return 0 if run_suite()["passed"] else 1

    if not args.prompt:
        parser.error("Provide --prompt or --run-suite")

    print(json.dumps(analyze_prompt(args.prompt).to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
