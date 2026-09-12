#!/usr/bin/env python3
"""Classify a heuristic into likely deterministic artifact types."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class ArtifactRule:
    name: str
    keywords: tuple[str, ...]
    recommendation: str


RULES = (
    ArtifactRule(
        "validator",
        ("must", "required", "missing", "forbid", "ensure", "check", "validate", "drift", "block"),
        "Encode the invariant as a yes/no check with actionable failures.",
    ),
    ArtifactRule(
        "normalizer",
        ("normalize", "canonical", "resize", "strip", "format", "sort", "compress", "mogrify", "metadata"),
        "Canonicalize noisy output before validation.",
    ),
    ArtifactRule(
        "generator",
        ("generate", "scaffold", "render", "emit", "create", "template", "managed"),
        "Move repeated file creation into a path-agnostic generator.",
    ),
    ArtifactRule(
        "manifest",
        ("manifest", "source of truth", "schema", "registry", "event list", "catalog"),
        "Store shared facts in one explicit source of truth.",
    ),
    ArtifactRule(
        "fixture",
        ("fixture", "golden", "snapshot", "regression", "example", "sample"),
        "Capture the failure with positive and negative fixtures.",
    ),
    ArtifactRule(
        "hook-or-ci-adapter",
        ("hook", "stop", "husky", "github actions", "ci", "pre-commit", "matrix"),
        "Call the same core script from hooks and CI adapters.",
    ),
    ArtifactRule(
        "docs-drift-check",
        ("docs", "documentation", "spec", "deprecated", "live check", "version", "api"),
        "Verify the live source before freezing spec-sensitive behavior.",
    ),
)


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9][a-z0-9-]*", text.lower()))


def score_rule(rule: ArtifactRule, text: str, tokens: set[str]) -> int:
    score = 0
    lowered = text.lower()
    for keyword in rule.keywords:
        if " " in keyword:
            if keyword in lowered:
                score += 2
        elif keyword in tokens:
            score += 1
    return score


def classify(text: str) -> dict[str, object]:
    tokens = tokenize(text)
    scored = [
        {
            "artifact": rule.name,
            "score": score_rule(rule, text, tokens),
            "recommendation": rule.recommendation,
        }
        for rule in RULES
    ]
    matches = [item for item in scored if item["score"] > 0]
    matches.sort(key=lambda item: (-int(item["score"]), str(item["artifact"])))
    return {
        "input": text,
        "primary": matches[0]["artifact"] if matches else "manual-review",
        "artifacts": matches,
        "note": (
            "No deterministic artifact was obvious. Ask for a repeatable failure mode or measurable invariant."
            if not matches
            else "Use this as a planning hint, then verify the invariant with fixtures."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="*", help="Heuristic or lesson text. Reads stdin when omitted.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    text = " ".join(args.text).strip()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        print("Provide heuristic text as arguments or stdin.", file=sys.stderr)
        return 1
    json.dump(classify(text), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
