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


WRITING_VERIFICATION = r"\bverif(?:y|ying)\b.{0,80}\b(?:rewrite|rewritten|revision|revised|edited|draft|prose|copy)\b"

PROSE_ACTIONS = (
    r"\b(?:adapt(?:ing)?|diagnos(?:e|ing)|draft(?:ing)?|write|rewrit(?:e|ing)|revis(?:e|ing)|edit(?:ed|ing)?|review(?:ing)?|polish(?:ing)?|tighten(?:ing)?|improv(?:e|ing)|clarif(?:y|ying)|human(?:ise|ize|ising|izing)|de-robot(?:ise|ize)|replac(?:e|ing)|remov(?:e|ing)|recast(?:ing)?|limit(?:ing)?|avoid(?:ed|ing|s)?|standardis(?:e|ing)|standardiz(?:e|ing))\b",
    r"\bmake\b.{0,80}\b(?:clearer|warmer|more\s+human|less\s+(?:stiff|generic|robotic))\b",
    WRITING_VERIFICATION,
    r"\b(?:genre|structure|format)\b",
)
PROSE_SCOPE = (
    r"\b(?:prose|copy|microcopy|sentence|paragraph|comment|document|draft|explanation|intro(?:duction)?|outro|heading|voice|tone|cadence|style|wording|slogan|tagline)\b",
    r"\b(?:announcement|notice|note|essay|poem|story|fiction|memo|email|cover\s+letter|newsletter|article|report|brief|proposal|bio|release\s+note|product\s+spec|pull\s+request|landing[- ]page|launch[- ]page|homepage|pricing\s+page)\b",
    r"\b(?:readme|guide|tutorial|how-to|runbook|walkthrough|documentation|docs|ui)\s+(?:draft|intro|section|copy|text|page)?\b",
    WRITING_VERIFICATION,
)
NEGATED_PROSE_CLAUSES = (
    r"\b(?:do\s+not|don't)\s+(?:(?:rewrite|edit|improve|revise|polish|humanise|humanize)\b(?:\s+or\s+)?){1,3}[^.;\n]*",
    r"\bthere\s+is\s+no\s+prose\b[^.;\n]*",
)
CODE_ONLY = (
    r"\b(?:debug|compile|build|deploy|implement|refactor|fix)\b.*\b(?:code|function|class|api|test|error|exception|stack trace|hydration|typescript|python|react|next\.js)\b",
    r"\b(?:why|how)\s+(?:does|do|can)\b.*\b(?:code|function|api|test|error|exception)\b",
    r"\b(?:replac(?:e|ing)|remov(?:e|ing)|recast(?:ing)?|limit(?:ing)?|avoid(?:ed|ing|s)?|standardis(?:e|ing)|standardiz(?:e|ing))\b.*\b(?:colons?|semi-?colons?|dashes|punctuation)\b.*\b(?:code|syntax|typescript|javascript|python|yaml|json|css|regex)\b",
)
FACT_CHECK_ONLY = (
    r"\b(?:fact[ -]?check|verify|validate|confirm)\b.*\b(?:fact|claim|source|citation|accuracy|true)\b",
    r"\b(?:is|are|was|were|does|do)\b.*\b(?:true|accurate|correct)\b",
)
DOCS_QUESTION = (
    r"\b(?:where|how)\s+(?:is|are|do i find|can i find)\b.*\b(?:docs|documentation|readme)\b",
    r"\b(?:what does|how does)\b.*\b(?:the docs|documentation|readme)\b",
)
PUNCTUATION_TRANSFORM = (
    r"\b(?:replac(?:e|ing)|remov(?:e|ing)|recast(?:ing)?|limit(?:ing)?|standardis(?:e|ing)|standardiz(?:e|ing))\b.{0,80}\b(?:em[ -]?dash(?:es)?|semi-?colons?|colons?|punctuation)\b",
    r"\b(?:em[ -]?dash(?:es)?|semi-?colons?|colons?|punctuation)\b.{0,80}\b(?:replac(?:e|ing)|remov(?:e|ing)|recast(?:ing)?|limit(?:ing)?|standardis(?:e|ing)|standardiz(?:e|ing))\b",
    r"\b(?:dash|semi-?colon|colon|punctuation)[ -]?(?:heavy|dense|awkward|overused)\b",
    r"\b(?:ban(?:ned|ning|s)?|avoid(?:ed|ing|s)?)\b.{0,80}\b(?:em[ -]?dash(?:es)?|semi-?colons?|colons|punctuation)\b",
    r"\b(?:em[ -]?dash(?:es)?|semi-?colons?|colons|punctuation)\b.{0,80}\b(?:ban(?:ned|ning|s)?|avoid(?:ed|ing|s)?)\b",
)
STRUCTURE_AND_DIGESTIBILITY = (
    r"\b(?:digestible|scannable|wall\s+of\s+text|dense\s+(?:paragraph|passage|prose)|overloaded\s+paragraph|long\s+(?:paragraph|passage|prose))\b",
    r"\b(?:break|split|chunk)\b.{0,60}\b(?:paragraph|passage|prose|text)\b",
    r"\b(?:restructur(?:e|ing)|reorgani[sz](?:e|ing)|reorder(?:ing)?)\b.{0,80}\b(?:paragraph|passage|prose|article|memo|report|guide|draft)\b",
    r"\b(?:natural|clearer|better)\s+(?:structure|flow)\b",
    r"\b(?:easier|easy)\s+to\s+scan\b",
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
    RouteRule("references/operating-contract.md", (r"\b(?:adapt(?:ing)?|diagnos(?:e|ing)|draft(?:ing)?|rewrit(?:e|ing)|revis(?:e|ing)|edit(?:ed|ing)?|review(?:ing)?|human(?:ise|ize|ising|izing)|verif(?:y|ying))\b",)),
    RouteRule("references/revision-pass-stack.md", (r"\b(?:adapt(?:ing)?|recast(?:ing)?|rewrit(?:e|ing)|rewritten|revis(?:e|ing)|revised|edit(?:ed|ing)?|polish(?:ing)?|tighten(?:ing)?|improv(?:e|ing)|cleanup|revision|draft(?:ing)?)\b",)),
    RouteRule("references/natural-structure-and-digestibility.md", STRUCTURE_AND_DIGESTIBILITY),
    RouteRule("references/foundations.md", (r"\b(?:clear|clarity|concise|grammar|usage|composition|basics?)\b",)),
    RouteRule("references/voice-and-rhythm.md", (r"\b(?:stiff|flat|bloodless|formal|robotic|cadence|rhythm|voice|owned|more\s+human|hedg(?:e|ing)|awkward|clipped)\b",)),
    RouteRule("references/punctuation-and-sentence-flow.md", PUNCTUATION_TRANSFORM),
    RouteRule("references/genericity-and-stiffness.md", (r"\b(?:generic|corporate|canned|fluffy|buzzwords?|over-signposted|dramatic|marketing[- ]speak|ceremonial)\b",)),
    RouteRule("references/ai-isms-and-humanisation.md", (r"\b(?:human(?:ise|ize)|ai[- ]?isms?|sound\s+(?:more\s+)?human|less\s+(?:robotic|ai)|machine[- ]?written)\b",)),
    RouteRule(
        "references/style-bundles.md",
        (
            r"\b(?:style|tone|publication|house[ -](?:style|voice)|voice\s+(?:sample|sheet|family)|operator\s+voice|newsletter\s+voice|editorial\s+voice|technical[ -]teacher\s+voice)\b",
            r"\b(?:simon\s+willison|julia\s+evans|gergely|lenny|reuters|bloomberg|paul\s+graham)\b",
        ),
    ),
    RouteRule("references/genre-modes.md", (r"\b(?:announcement|notice|guide|tutorial|how-to|docs?|readme|runbook|memo|brief|report|essay|article|landing[- ]page|launch[- ]page|homepage|pricing\s+page|email|walkthrough)\b",)),
    RouteRule(
        "references/quality-gates.md",
        (r"\b(?:final\s+(?:review|pass|check)|ready\s+to\s+publish|quality\s+check|sign[- ]?off)\b", WRITING_VERIFICATION),
    ),
    RouteRule("references/gotchas.md", (r"\b(?:over-edit(?:ed|ing)?|already\s+been\s+edited|edited\s+(?:two|three|multiple)\s+times|getting\s+worse|each\s+pass|too\s+polished|modes?\s+conflict|conflicting\s+(?:genres?|modes?)|can'?t\s+get\s+this\s+right)\b",)),
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
        ("references/punctuation-and-sentence-flow.md",),
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
        ("references/punctuation-and-sentence-flow.md",),
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
        ("references/operating-contract.md", "references/genre-modes.md"),
        ("references/style-bundles.md",),
    ),
    TestCase(
        "explicit_publication_style",
        "Rewrite this report in a Reuters-style, fact-first tone without copying signature phrasing.",
        (
            "references/operating-contract.md",
            "references/revision-pass-stack.md",
            "references/style-bundles.md",
            "references/genre-modes.md",
        ),
    ),
    TestCase(
        "slogan_draft",
        "Draft a new product slogan from scratch, but ask for the minimum audience context first.",
        ("references/operating-contract.md", "references/revision-pass-stack.md"),
    ),
    TestCase(
        "replace_em_dashes_by_relation",
        "Rewrite these sentences to replace the em dashes with natural punctuation and sentence structures; use semicolons and colons only where their grammar and relation fit.",
        (
            "references/operating-contract.md",
            "references/revision-pass-stack.md",
            "references/punctuation-and-sentence-flow.md",
        ),
    ),
    TestCase(
        "repair_punctuation_heavy_prose",
        "Edit this punctuation-heavy paragraph so the flow is less awkward without changing its meaning.",
        (
            "references/operating-contract.md",
            "references/revision-pass-stack.md",
            "references/voice-and-rhythm.md",
            "references/punctuation-and-sentence-flow.md",
        ),
    ),
    TestCase(
        "restructure_dense_analysis",
        "Rewrite this long, dense analysis into digestible prose without turning every sentence into a bullet.",
        (
            "references/operating-contract.md",
            "references/revision-pass-stack.md",
            "references/natural-structure-and-digestibility.md",
        ),
        ("references/punctuation-and-sentence-flow.md",),
    ),
    TestCase(
        "eval_2_exact_memo_route",
        "Rewrite the attached Q3 operations memo for an executive audience. Make the argument easier to scan and less corporate, but preserve 18.4%, Q3, the sentence `We have not tested this in production.`, the quoted sentence, and the uncertainty word `may`. Do not add a source, result, or personal experience.",
        (
            "references/operating-contract.md",
            "references/revision-pass-stack.md",
            "references/natural-structure-and-digestibility.md",
            "references/genericity-and-stiffness.md",
            "references/genre-modes.md",
        ),
        (
            "references/style-bundles.md",
            "references/voice-and-rhythm.md",
            "references/research-notes.md",
        ),
    ),
    TestCase(
        "eval_20_exact_dense_analysis_route",
        "Rewrite the attached renewal-pilot analysis for product and engineering readers. Make it digestible by separating the finding, evidence limit, operational consequence, and recommendation where their jobs change. Preserve every number, both uses of `may`, `awaiting_confirmation`, the quoted sentence, and the unresolved callback cause. Do not turn every sentence into its own paragraph, use bullets unless the items are genuine peers, or publish diagnostic labels as headings in this short update.",
        (
            "references/operating-contract.md",
            "references/revision-pass-stack.md",
            "references/natural-structure-and-digestibility.md",
        ),
        (
            "references/quality-gates.md",
            "references/punctuation-and-sentence-flow.md",
            "references/research-notes.md",
        ),
    ),
    TestCase(
        "eval_21_exact_dense_runbook_route",
        "Rewrite the attached long paragraph about staging key rotation as a compact runbook. Use numbered steps for meaningful checkpoints, not every small verb; make the `issuer mismatch` stop condition unmistakable and end with verification. Preserve every command, `kid`, `staging.env`, `issuer mismatch`, `test-user`, and `<old-kid>` exactly. Do not invent a rollback command or claim the rotation succeeded.",
        (
            "references/operating-contract.md",
            "references/revision-pass-stack.md",
            "references/natural-structure-and-digestibility.md",
            "references/genre-modes.md",
        ),
        ("references/research-notes.md",),
    ),
    TestCase("code_only_rewrite", "Rewrite this Python function to remove a race condition.", (), ("references/operating-contract.md",)),
    TestCase(
        "code_punctuation_replacement",
        "Replace the colons in this YAML syntax with equals signs.",
        (),
        ("references/punctuation-and-sentence-flow.md",),
    ),
    TestCase(
        "code_em_dash_replacement",
        "Remove the em dashes from these TypeScript comments and return the code patch only.",
        (),
        ("references/punctuation-and-sentence-flow.md",),
    ),
    TestCase(
        "colon_topic_not_punctuation",
        "Draft a plain-language article about colon cancer screening.",
        (
            "references/operating-contract.md",
            "references/revision-pass-stack.md",
            "references/genre-modes.md",
        ),
        ("references/punctuation-and-sentence-flow.md",),
    ),
    TestCase("fact_check_only", "Fact-check whether this claim about GDP is accurate.", (), ("references/foundations.md",)),
    TestCase(
        "verify_report_claims_only",
        "Verify whether this report's claims are accurate; do not rewrite it.",
        (),
        ("references/operating-contract.md", "references/revision-pass-stack.md", "references/genre-modes.md"),
    ),
    TestCase(
        "verify_rewritten_report_preservation",
        "Verify that this rewritten report preserves every number and quote.",
        (
            "references/operating-contract.md",
            "references/revision-pass-stack.md",
            "references/genre-modes.md",
            "references/quality-gates.md",
        ),
        ("references/research-notes.md",),
    ),
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

    positive_text = text
    for pattern in NEGATED_PROSE_CLAUSES:
        positive_text = re.sub(pattern, " ", positive_text, flags=re.IGNORECASE)
    action = matches_any(positive_text, PROSE_ACTIONS)
    scope = matches_any(positive_text, PROSE_SCOPE)
    punctuation_transform = matches_any(positive_text, PUNCTUATION_TRANSFORM)
    if matches_any(text, FACT_CHECK_ONLY) and not action:
        return False
    if matches_any(text, DOCS_QUESTION) and not action:
        return False
    if matches_any(text, CODE_ONLY) and not scope:
        return False
    return action and (scope or punctuation_transform)


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
