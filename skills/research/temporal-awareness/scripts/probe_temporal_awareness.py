#!/usr/bin/env python3
"""Run deterministic regression checks for the temporal-awareness skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import capture_temporal_context
import recency_guard


TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T")
OFFSET_RE = re.compile(r"^[+-]\d{2}:\d{2}$")


def run_suite() -> dict:
    checks = []
    passed = 0

    context = capture_temporal_context.capture_context(["America/New_York", "UTC"])

    def record(name: str, condition: bool, detail: str) -> None:
        nonlocal passed
        if condition:
            passed += 1
        checks.append({"name": name, "passed": condition, "detail": detail})

    record(
        "context-local-iso",
        bool(TIME_RE.match(context["local"]["iso"])),
        f"local.iso={context['local']['iso']}",
    )
    record(
        "context-utc-iso",
        bool(TIME_RE.match(context["utc"]["iso"])),
        f"utc.iso={context['utc']['iso']}",
    )
    record(
        "context-primary-timezone",
        bool(context["timezone"]["primary"]),
        f"primary={context['timezone']['primary']}",
    )
    record(
        "context-offset-shape",
        bool(OFFSET_RE.match(context["timezone"]["utc_offset"])),
        f"offset={context['timezone']['utc_offset']}",
    )
    record(
        "context-extra-zone-count",
        len(context["extra_zones"]) == 2,
        f"extra_zones={len(context['extra_zones'])}",
    )

    cases = [
        {
            "name": "clock-only-date",
            "prompt": "What's today's date here and in UTC?",
            "mode": "system-clock",
            "live": False,
            "anchor": True,
        },
        {
            "name": "latest-model",
            "prompt": "What is the latest OpenAI model for coding right now?",
            "mode": "live-verify",
            "live": True,
            "anchor": True,
        },
        {
            "name": "relative-comparison",
            "prompt": "Compare what changed yesterday versus today.",
            "mode": "live-verify",
            "live": True,
            "anchor": True,
        },
        {
            "name": "stable-historical",
            "prompt": "Who won the 2024 US presidential election?",
            "mode": "system-clock",
            "live": False,
            "anchor": True,
        },
        {
            "name": "timeless-technical",
            "prompt": "Explain the TCP three-way handshake.",
            "mode": "stable",
            "live": False,
            "anchor": False,
        },
        {
            "name": "live-role",
            "prompt": "Is Sam Altman still the CEO of OpenAI?",
            "mode": "live-verify",
            "live": True,
            "anchor": True,
        },
        {
            "name": "clock-zone-conversion",
            "prompt": "What date is it in New York right now?",
            "mode": "system-clock",
            "live": False,
            "anchor": True,
        },
    ]

    for case in cases:
        result = recency_guard.analyze_prompt(case["prompt"])
        record(
            f"{case['name']}-mode",
            result["mode"] == case["mode"],
            f"expected={case['mode']} actual={result['mode']}",
        )
        record(
            f"{case['name']}-live",
            result["requires_live_verification"] is case["live"],
            f"expected={case['live']} actual={result['requires_live_verification']}",
        )
        record(
            f"{case['name']}-anchor",
            result["requires_temporal_anchor"] is case["anchor"],
            f"expected={case['anchor']} actual={result['requires_temporal_anchor']}",
        )

    total = len(checks)
    return {
        "passed": passed == total,
        "summary": {
            "checks_passed": passed,
            "checks_total": total,
        },
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--format",
        choices=["json", "pretty"],
        default="pretty",
        help="Output format.",
    )
    args = parser.parse_args()

    results = run_suite()
    if args.format == "json":
        json.dump(results, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        summary = results["summary"]
        print(
            f"Temporal awareness probe: {summary['checks_passed']}/{summary['checks_total']} checks passed"
        )
        for check in results["checks"]:
            marker = "PASS" if check["passed"] else "FAIL"
            print(f"- {marker} {check['name']}: {check['detail']}")

    return 0 if results["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
