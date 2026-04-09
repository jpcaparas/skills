#!/usr/bin/env python3
"""Classify whether a prompt needs a temporal anchor or live verification."""

from __future__ import annotations

import argparse
import json
import re
import sys

RELATIVE_PATTERNS = [
    r"\blatest\b",
    r"\bcurrent(?:ly)?\b",
    r"\bnow\b",
    r"\bright now\b",
    r"\btoday\b",
    r"\byesterday\b",
    r"\btomorrow\b",
    r"\btonight\b",
    r"\brecent(?:ly)?\b",
    r"\bas of\b",
    r"\bstill\b",
    r"\bthis week\b",
    r"\bthis month\b",
    r"\bthis year\b",
    r"\blast week\b",
    r"\bnext week\b",
    r"\bupcoming\b",
]

VOLATILE_GROUPS = {
    "clock": [
        r"\bdate\b",
        r"\btime\b",
        r"\btimezone\b",
        r"\btime zone\b",
        r"\blocal time\b",
        r"\bwhat day\b",
    ],
    "models_versions": [
        r"\bmodel(?:s)?\b",
        r"\bversion(?:s)?\b",
        r"\brelease(?:d|s)?\b",
        r"\brollout\b",
        r"\bavailability\b",
        r"\bcontext window\b",
        r"\bpricing\b",
        r"\brate limit(?:s)?\b",
    ],
    "market_data": [
        r"\bstock\b",
        r"\bshare price\b",
        r"\bmarket cap\b",
        r"\bcrypto\b",
        r"\bexchange rate\b",
        r"\bprice\b",
    ],
    "roles_orgs": [
        r"\bceo\b",
        r"\bcfo\b",
        r"\bpresident\b",
        r"\bprime minister\b",
        r"\bgovernor\b",
        r"\bchair(?:man|person)\b",
    ],
    "laws_rules": [
        r"\blaw(?:s)?\b",
        r"\bregulation(?:s)?\b",
        r"\bpolicy\b",
        r"\btax\b",
        r"\bcompliance\b",
    ],
    "live_events": [
        r"\bweather\b",
        r"\bscore(?:s)?\b",
        r"\bstandings\b",
        r"\bschedule(?:s)?\b",
        r"\bflight status\b",
        r"\bheadline(?:s)?\b",
        r"\bnews\b",
    ],
}

EXPLICIT_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
ISO_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
MONTH_DATE_RE = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?) "
    r"\d{1,2}, \d{4}\b",
    re.IGNORECASE,
)


def collect_matches(prompt: str, patterns: list[str]) -> list[str]:
    matches = []
    for pattern in patterns:
        for match in re.finditer(pattern, prompt, flags=re.IGNORECASE):
            term = match.group(0).lower()
            if term not in matches:
                matches.append(term)
    return matches


def analyze_prompt(prompt: str) -> dict:
    lowered = prompt.lower()
    relative_terms = collect_matches(lowered, RELATIVE_PATTERNS)
    explicit_years = EXPLICIT_YEAR_RE.findall(prompt)
    explicit_dates = ISO_DATE_RE.findall(prompt) + MONTH_DATE_RE.findall(prompt)

    categories = {}
    for category, patterns in VOLATILE_GROUPS.items():
        matches = collect_matches(lowered, patterns)
        if matches:
            categories[category] = matches

    has_relative = bool(relative_terms)
    has_clock = "clock" in categories
    volatile_non_clock = any(category != "clock" for category in categories)
    stable_historical = bool((explicit_years or explicit_dates) and not has_relative)

    if has_clock and not volatile_non_clock:
        mode = "system-clock"
        requires_live_verification = False
        requires_temporal_anchor = True
    elif has_relative or (volatile_non_clock and not stable_historical):
        mode = "live-verify"
        requires_live_verification = True
        requires_temporal_anchor = True
    elif has_clock or explicit_dates or explicit_years:
        mode = "system-clock"
        requires_live_verification = False
        requires_temporal_anchor = True
    else:
        mode = "stable"
        requires_live_verification = False
        requires_temporal_anchor = False

    reasons = []
    if has_relative:
        reasons.append("Relative-time language is present.")
    if volatile_non_clock and not stable_historical:
        reasons.append("The prompt references a volatile external domain.")
    if has_clock:
        reasons.append("The prompt depends on local date, time, or timezone interpretation.")
    if stable_historical:
        reasons.append("The prompt includes an explicit historical date or year without current-state language.")
    if not reasons:
        reasons.append("The prompt appears stable and not time-sensitive.")

    actions = []
    if requires_live_verification:
        actions.extend(
            [
                "Capture the current local and UTC time first.",
                "Verify the claim against an authoritative live source before answering.",
                "State the exact date and timezone used in the answer.",
            ]
        )
    elif requires_temporal_anchor:
        actions.extend(
            [
                "Capture the local and UTC time before answering.",
                "Convert relative or cross-zone references into absolute dates or times.",
            ]
        )
    else:
        actions.append("Answer normally; live verification is optional unless the user explicitly asks for it.")

    return {
        "prompt": prompt,
        "mode": mode,
        "risk_level": "high" if requires_live_verification else "medium" if requires_temporal_anchor else "low",
        "requires_temporal_anchor": requires_temporal_anchor,
        "requires_live_verification": requires_live_verification,
        "relative_terms": relative_terms,
        "matched_categories": categories,
        "explicit_years": explicit_years,
        "explicit_dates": explicit_dates,
        "stable_historical": stable_historical,
        "reasons": reasons,
        "recommended_actions": actions,
    }


def render_markdown(result: dict) -> str:
    lines = [
        "# Recency Guard",
        "",
        f"- Mode: `{result['mode']}`",
        f"- Risk level: `{result['risk_level']}`",
        f"- Requires temporal anchor: `{str(result['requires_temporal_anchor']).lower()}`",
        f"- Requires live verification: `{str(result['requires_live_verification']).lower()}`",
    ]

    if result["relative_terms"]:
        lines.append(f"- Relative terms: `{', '.join(result['relative_terms'])}`")
    if result["explicit_years"] or result["explicit_dates"]:
        combined = result["explicit_dates"] + result["explicit_years"]
        lines.append(f"- Explicit dates: `{', '.join(combined)}`")
    if result["matched_categories"]:
        categories = ", ".join(sorted(result["matched_categories"]))
        lines.append(f"- Matched categories: `{categories}`")

    lines.extend(["", "## Reasons", ""])
    for reason in result["reasons"]:
        lines.append(f"- {reason}")

    lines.extend(["", "## Recommended Actions", ""])
    for action in result["recommended_actions"]:
        lines.append(f"- {action}")

    return "\n".join(lines)


def render_text(result: dict) -> str:
    return "\n".join(
        [
            f"mode={result['mode']}",
            f"risk_level={result['risk_level']}",
            f"requires_temporal_anchor={str(result['requires_temporal_anchor']).lower()}",
            f"requires_live_verification={str(result['requires_live_verification']).lower()}",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True, help="Prompt to classify.")
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "text"],
        default="json",
        help="Output format.",
    )
    args = parser.parse_args()

    result = analyze_prompt(args.prompt)

    if args.format == "json":
        json.dump(result, sys.stdout, indent=2)
        sys.stdout.write("\n")
    elif args.format == "markdown":
        sys.stdout.write(render_markdown(result))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(render_text(result))
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
