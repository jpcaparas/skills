#!/usr/bin/env python3
"""
verify_docs.py

Check the live official GitHub Copilot hook docs for the contract this skill
scaffolds against.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path


DOCS = {
    "concepts": "https://raw.githubusercontent.com/github/docs/main/content/copilot/concepts/agents/hooks.md",
    "cli": "https://raw.githubusercontent.com/github/docs/main/content/copilot/how-tos/copilot-cli/customize-copilot/use-hooks.md",
    "cli_example_steps": "https://raw.githubusercontent.com/github/docs/main/data/reusables/copilot/cloud-agent/hooks-example-steps.md",
    "reference": "https://raw.githubusercontent.com/github/docs/main/content/copilot/reference/hooks-reference.md",
}

EXPECTED_EVENTS = [
    "sessionStart",
    "sessionEnd",
    "userPromptSubmitted",
    "preToolUse",
    "postToolUse",
    "postToolUseFailure",
    "agentStop",
    "subagentStart",
    "subagentStop",
    "errorOccurred",
    "preCompact",
    "permissionRequest",
    "notification",
]


def fetch(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "scaffold-github-copilot-hooks/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def check_docs() -> dict:
    errors: list[str] = []
    sources: dict[str, str] = {}
    docs: dict[str, str] = {}

    for name, url in DOCS.items():
        sources[name] = url
        try:
            docs[name] = fetch(url)
        except Exception as exc:  # pragma: no cover - depends on network
            errors.append(f"Could not fetch {name} docs: {exc}")
            docs[name] = ""

    concepts = docs.get("concepts", "")
    cli = docs.get("cli", "") + "\n" + docs.get("cli_example_steps", "")
    reference = docs.get("reference", "")

    concepts_needles = [
        ".github/hooks/*.json",
        "~/.copilot/hooks/*.json",
        '"version": 1',
        '"hooks"',
        "preToolUse",
    ]
    for needle in concepts_needles:
        if needle not in concepts:
            errors.append(f"Concept docs missing expected text: {needle}")

    cli_needles = [
        ".github/hooks/",
        "~/.copilot/hooks/",
        "COPILOT_HOME",
        "loaded when the CLI starts",
    ]
    for needle in cli_needles:
        if needle not in cli:
            errors.append(f"CLI docs missing expected text: {needle}")

    for event_name in EXPECTED_EVENTS:
        if not re.search(rf"`{re.escape(event_name)}`", reference):
            errors.append(f"Reference docs missing expected event: {event_name}")

    reference_needles = [
        "Command hooks",
        "HTTP hooks",
        "Prompt hooks",
        "permissionDecision",
        "permissionRequest",
        "exit `2` is treated as",
        "preToolUse` is fail-closed",
        "disableAllHooks",
        "matcher",
        "Cloud agent",
        ".github/hooks/*.json",
        "$COPILOT_HOME/hooks",
    ]
    for needle in reference_needles:
        if needle not in reference:
            errors.append(f"Reference docs missing expected text: {needle}")

    return {
        "valid": not errors,
        "sources": sources,
        "expected_events": EXPECTED_EVENTS,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify live official GitHub Copilot hook docs.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    result = check_docs()
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("GitHub Copilot hook docs:", "valid" if result["valid"] else "invalid")
        for error in result["errors"]:
            print(f"- {error}")

    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
