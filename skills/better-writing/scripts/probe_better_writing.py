#!/usr/bin/env python3
"""Route genuine prose work to the smallest useful better-writing references.

Usage:
    python3 probe_better_writing.py --prompt "..."
    python3 probe_better_writing.py --suite
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from typing import Sequence


PROSE_ACTIONS = (
    r"\b(?:draft(?:ing)?|write|rewrit(?:e|ing)|edit(?:ing)?|review(?:ing)?|polish(?:ing)?|tighten(?:ing)?|improv(?:e|ing)|clarif(?:y|ying)|human(?:ise|ize|ising|izing)|de-robot(?:ise|ize))\b",
    r"\bmake\s+(?:this|it)\s+(?:clearer|warmer|less\s+(?:stiff|generic|robotic))\b",
    r"\b(?:genre|structure|format)\b",
)
PROSE_SCOPE = (
    r"\b(?:prose|copy|microcopy|sentence|paragraph|comment|intro(?:duction)?|outro|heading|voice|tone|cadence|style|wording|slogan|tagline)\b",
    r"\b(?:essay|poem|story|fiction|memo|email|cover\s+letter|newsletter|article|report|brief|proposal|bio|release\s+note|product\s+spec|pull\s+request|landing\s+page|homepage|pricing\s+page)\b",
    r"\b(?:readme|guide|tutorial|how-to|runbook|walkthrough|documentation|docs|ui)\s+(?:draft|intro|section|copy|text|page)?\b",
)
CODE_ONLY = (
    r"\b(?:debug|compile|build|deploy|implement|refactor|fix)\b.*\b(?:code|function|class|api|test|error|exception|stack trace|hydration|typescript|python|react|next\.js)\b",
    r"\b(?:why|how)\s+(?:does|do|can)\b.*\b(?:code|function|api|test|error|exception)\b",
)
FACT_CHECK_ONLY = (
    r"\b(?:fact[ -]?check|verify|validate|confirm)\b.*\b(?:fact|claim|source|citation|accuracy|true)\b",
    r"\b(?:is|are|was|were|does|do)\b.*\b(?:true|accurate|correct)\b",
)
DOCS_QUESTION = (
    r"\b(?:where|how)\s+(?:is|are|do i find|can i find)\b.*\b(?:docs|documentation|readme)\b",
    r"\b(?:what does|how does)\b.*\b(?:the docs|documentation|readme)\b",
)


@dataclass(frozen=True)
class RouteRule:
    reference: str
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class TestCase:
    name: str
    prompt: str
    expect: tuple[str, ...]
    forbid: tuple[str, ...] = ()


ROUTE_RULES = (
    RouteRule("references/operating-contract.md", (r"\b(?:draft(?:ing)?|rewrit(?:e|ing)|edit(?:ing)?|review(?:ing)?|human(?:ise|ize|ising|izing))\b",)),
    RouteRule("references/revision-pass-stack.md", (r"\b(?:rewrit(?:e|ing)|edit(?:ing)?|polish(?:ing)?|tighten(?:ing)?|improv(?:e|ing)|cleanup|revision|draft(?:ing)?)\b",)),
    RouteRule("references/foundations.md", (r"\b(?:clear|clarity|concise|grammar|usage|composition|basics?)\b",)),
    RouteRule("references/voice-and-rhythm.md", (r"\b(?:stiff|flat|bloodless|formal|robotic|cadence|rhythm|hedg(?:e|ing)|awkward|clipped)\b",)),
    RouteRule("references/genericity-and-stiffness.md", (r"\b(?:generic|corporate|canned|fluffy|buzzwords?|over-signposted|dramatic|marketing[- ]speak|ceremonial)\b",)),
    RouteRule("references/ai-isms-and-humanisation.md", (r"\b(?:human(?:ise|ize)|ai[- ]?isms?|sound\s+human|less\s+(?:robotic|ai)|machine[- ]?written)\b",)),
    RouteRule("references/style-bundles.md", (r"\b(?:style|tone|publication|operator|newsletter|editorial|essay|memo|copy|simon\s+willison|julia\s+evans|gergely|lenny|reuters|bloomberg|paul\s+graham)\b",)),
    RouteRule("references/genre-modes.md", (r"\b(?:guide|tutorial|how-to|docs?|readme|runbook|memo|brief|report|essay|article|landing\s+page|homepage|pricing\s+page|email|walkthrough)\b",)),
    RouteRule("references/quality-gates.md", (r"\b(?:final\s+(?:review|pass|check)|ready\s+to\s+publish|quality\s+check|sign[- ]?off)\b",)),
    RouteRule("references/gotchas.md", (r"\b(?:over-edit(?:ed|ing)?|getting\s+worse|each\s+pass|too\s+polished|can'?t\s+get\s+this\s+right)\b",)),
)


TEST_CASES = (
    TestCase(
        "humanise_mixed_docs_scope",
        "Humanise the prose in this React README introduction without changing the code example.",
        (
            "references/operating-contract.md",
            "references/ai-isms-and-humanisation.md",
            "references/genre-modes.md",
        ),
    ),
    TestCase(
        "stiff_runbook_intro",
        "Review and rewrite this runbook intro. It is clear but still stiff and corporate.",
        (
            "references/operating-contract.md",
            "references/revision-pass-stack.md",
            "references/voice-and-rhythm.md",
            "references/genericity-and-stiffness.md",
            "references/genre-modes.md",
        ),
    ),
    TestCase(
        "genre_draft",
        "Draft a concise launch email for existing customers, then give it a final quality check.",
        (
            "references/operating-contract.md",
            "references/revision-pass-stack.md",
            "references/genre-modes.md",
            "references/quality-gates.md",
        ),
    ),
    TestCase(
        "genre_question",
        "What genre and structure should this reflective essay use before I start drafting?",
        ("references/operating-contract.md", "references/style-bundles.md", "references/genre-modes.md"),
    ),
    TestCase(
        "slogan_draft",
        "Draft a new product slogan from scratch, but ask for the minimum audience context first.",
        ("references/operating-contract.md", "references/revision-pass-stack.md"),
    ),
    TestCase("code_only_rewrite", "Rewrite this Python function to remove a race condition.", (), ("references/operating-contract.md",)),
    TestCase("fact_check_only", "Fact-check whether this claim about GDP is accurate.", (), ("references/foundations.md",)),
    TestCase("docs_question", "Where do I find the API documentation for this option?", (), ("references/genre-modes.md",)),
)


def matches_any(text: str, patterns: Sequence[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def add_unique(items: list[str], new_items: Sequence[str]) -> None:
    for item in new_items:
        if item not in items:
            items.append(item)


def has_prose_request(text: str) -> bool:
    """Accept prose work, including prose embedded in an otherwise technical prompt."""

    action = matches_any(text, PROSE_ACTIONS)
    scope = matches_any(text, PROSE_SCOPE)
    if matches_any(text, FACT_CHECK_ONLY) and not action:
        return False
    if matches_any(text, DOCS_QUESTION) and not action:
        return False
    if matches_any(text, CODE_ONLY) and not scope:
        return False
    return action and scope


def route_prompt(prompt: str) -> list[str]:
    """Return references only when the prompt clearly asks for prose help."""

    text = prompt.strip().lower()
    if not text or not has_prose_request(text):
        return []
    references: list[str] = []
    for rule in ROUTE_RULES:
        if matches_any(text, rule.patterns):
            add_unique(references, (rule.reference,))
    if "references/operating-contract.md" not in references:
        references.insert(0, "references/operating-contract.md")
    if not references:
        references.extend(("references/operating-contract.md", "references/foundations.md"))
    return references


def run_case(case: TestCase) -> dict[str, object]:
    references = route_prompt(case.prompt)
    missing = [reference for reference in case.expect if reference not in references]
    forbidden = [reference for reference in case.forbid if reference in references]
    passed = not missing and not forbidden and (bool(case.expect) or not references)
    return {
        "name": case.name,
        "passed": passed,
        "expected": list(case.expect),
        "forbidden": list(case.forbid),
        "actual": references,
        "missing": missing,
        "unexpected": forbidden,
    }


def run_suite() -> dict[str, object]:
    checks = [run_case(case) for case in TEST_CASES]
    return {
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "summary": {"checks_total": len(checks), "checks_passed": sum(1 for check in checks if check["passed"])},
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Route clear prose requests to better-writing references.")
    parser.add_argument("--prompt", help="Prompt to route")
    parser.add_argument("--suite", action="store_true", help="Run the built-in routing suite")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Output format")
    args = parser.parse_args(argv)
    if args.suite:
        result: dict[str, object] = run_suite()
    elif args.prompt:
        result = {"prompt": args.prompt, "references": route_prompt(args.prompt)}
    else:
        parser.error("pass --prompt or --suite")
    if args.format == "json":
        print(json.dumps(result, indent=2))
    elif args.suite:
        summary = result["summary"]
        assert isinstance(summary, dict)
        print(f"Suite: {summary['checks_passed']}/{summary['checks_total']} passed")
        for check in result["checks"]:
            assert isinstance(check, dict)
            print(f"{'PASS' if check['passed'] else 'FAIL'}: {check['name']}")
    else:
        references = result["references"]
        assert isinstance(references, list)
        print("Recommended references:" if references else "No prose-writing route detected.")
        for reference in references:
            print(f"- {reference}")
    return 0 if not args.suite or bool(result["passed"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
