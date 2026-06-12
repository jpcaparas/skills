#!/usr/bin/env python3
"""
verify_docs.py

Fetch the official Devin hook docs and verify the local scaffold contract still
matches the documented event names, hook file path, matcher rules, environment
variable, and exit-code semantics.

Usage:
    python3 verify_docs.py [--json]
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request


SOURCES = {
    "overview": "https://docs.devin.ai/cli/extensibility/hooks/overview",
    "lifecycle": "https://docs.devin.ai/cli/extensibility/hooks/lifecycle-hooks",
}

EXPECTED_EVENTS = [
    "PreToolUse",
    "PostToolUse",
    "PermissionRequest",
    "UserPromptSubmit",
    "Stop",
    "PostCompaction",
    "SessionStart",
    "SessionEnd",
]

EXPECTED_SNIPPETS = {
    "overview": [
        ".devin/hooks.v1.json",
        "DEVIN_PROJECT_DIR",
        "Exit Codes",
        "2 Block",
        "hooks object is the entire file",
    ],
    "lifecycle": [
        "Using the Matcher",
        "regex matched against",
        "mcp__<server>__<tool>",
        "stop_hook_active",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def fetch_text(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "scaffold-hooks-devin-doc-check/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read().decode("utf-8", errors="replace")

    without_scripts = re.sub(r"<(script|style)\b[\s\S]*?</\1>", " ", raw, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", without_scripts)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text)


def main() -> int:
    args = parse_args()
    pages: dict[str, str] = {}
    errors: list[str] = []

    for name, url in SOURCES.items():
        try:
            pages[name] = fetch_text(url)
        except Exception as exc:  # pragma: no cover - network boundary
            errors.append(f"Failed to fetch {url}: {exc}")
            pages[name] = ""

    for event in EXPECTED_EVENTS:
        if event not in pages.get("lifecycle", ""):
            errors.append(f"Lifecycle docs do not mention expected event: {event}")

    for page_name, snippets in EXPECTED_SNIPPETS.items():
        page_text = pages.get(page_name, "")
        for snippet in snippets:
            if snippet not in page_text:
                errors.append(f"{page_name} docs missing expected snippet: {snippet}")

    result = {
        "valid": not errors,
        "sources": SOURCES,
        "expected_events": EXPECTED_EVENTS,
        "errors": errors,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("Devin hook docs verification")
        for name, url in SOURCES.items():
            print(f"  {name}: {url}")
        print(f"  events checked: {', '.join(EXPECTED_EVENTS)}")
        if errors:
            print()
            print("Issues:")
            for error in errors:
                print(f"  - {error}")
        print()
        print("PASS: docs match expected hook contract" if result["valid"] else "FAIL: docs drift detected")

    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
