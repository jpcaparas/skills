#!/usr/bin/env python3
"""
build_fix_prompt.py — Build a second-session SEO remediation prompt from findings JSON.

Usage:
    python3 build_fix_prompt.py --input findings.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


TEMPLATE_NAME = "fix-prompt-template.md"


def load_template(script_dir: Path) -> str:
    template_path = script_dir.parent / "templates" / TEMPLATE_NAME
    return template_path.read_text(encoding="utf-8")


def normalize_findings(findings: list[dict]) -> list[dict]:
    normalized = []
    for finding in findings:
        severity = str(finding.get("severity", "medium")).lower()
        category = str(finding.get("category", "seo")).strip()
        scope = str(finding.get("scope", "unknown scope")).strip()
        evidence = str(finding.get("evidence", "No evidence provided.")).strip()
        fix_direction = str(finding.get("fix_direction", "Determine the smallest safe fix.")).strip()
        normalized.append(
            {
                "severity": severity,
                "category": category,
                "scope": scope,
                "evidence": evidence,
                "fix_direction": fix_direction,
            }
        )
    order = {"blocker": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(normalized, key=lambda item: (order.get(item["severity"], 9), item["category"], item["scope"]))


def bullet_list(items: list[str], default: str) -> str:
    clean = [item.strip() for item in items if item and item.strip()]
    if not clean:
        clean = [default]
    return "\n".join(f"- {item}" for item in clean)


def format_findings(findings: list[dict]) -> str:
    lines = []
    for idx, finding in enumerate(findings, start=1):
        lines.append(
            f"{idx}. [{finding['severity'].upper()}] {finding['category']} | {finding['scope']} | "
            f"Evidence: {finding['evidence']} | Fix direction: {finding['fix_direction']}"
        )
    return "\n".join(lines) if lines else "1. [MEDIUM] seo | unknown scope | Evidence: No findings provided. | Fix direction: Confirm the audit before making changes."


def format_work_items(findings: list[dict]) -> str:
    lines = []
    for idx, finding in enumerate(findings, start=1):
        lines.append(f"{idx}. Fix `{finding['category']}` for `{finding['scope']}` by applying this direction: {finding['fix_direction']}")
    return "\n".join(lines) if lines else "1. Re-run the audit and confirm the root causes before editing code."


def format_acceptance_criteria(findings: list[dict]) -> str:
    lines = []
    for finding in findings:
        category = finding["category"]
        scope = finding["scope"]
        if category == "metadata":
            lines.append(f"- `{scope}` emits route-correct title, description, canonical, and social metadata in rendered HTML.")
        elif category == "canonical":
            lines.append(f"- `{scope}` resolves to the intended canonical URL strategy with no contradictory signals.")
        elif category == "schema":
            lines.append(f"- `{scope}` emits valid schema aligned to visible page content and page purpose.")
        elif category == "crawlability":
            lines.append(f"- `{scope}` is crawlable and indexable exactly when intended, with correct robots and status behavior.")
        else:
            lines.append(f"- `{scope}` satisfies the validated `{category}` fix without regressions in rendered output.")
    if not lines:
        lines.append("- Confirm the audited issue has been fixed in rendered output, not just in source code.")
    return "\n".join(lines)


def render_prompt(data: dict, template: str) -> str:
    findings = normalize_findings(data.get("findings", []))
    replacements = {
        "{{REPO_PATH}}": str(data.get("repo", os.getcwd())),
        "{{OBJECTIVE}}": str(data.get("objective", "Resolve the confirmed SEO issues in this repository.")),
        "{{STACK}}": str(data.get("stack", "Unknown")),
        "{{PAGES_OR_TEMPLATES}}": "\n  - ".join(data.get("pages_or_templates", ["Identify and update the affected shared templates and routes."])),
        "{{CONFIRMED_FINDINGS}}": format_findings(findings),
        "{{EXTRA_CONSTRAINTS}}": str(data.get("extra_constraints", "Preserve existing UX and intended routing semantics.")),
        "{{WORK_ITEMS}}": format_work_items(findings),
        "{{ACCEPTANCE_CRITERIA}}": format_acceptance_criteria(findings),
        "{{VERIFICATION_COMMANDS}}": bullet_list(
            data.get("verification_commands", []),
            "Run the repo's relevant build, test, lint, and rendered-output checks.",
        ),
    }
    output = template
    for needle, value in replacements.items():
        output = output.replace(needle, value)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a second-session SEO fix prompt from findings JSON.")
    parser.add_argument("--input", required=True, help="Path to findings JSON.")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.is_file():
        print(f"Input file not found: {input_path}", file=sys.stderr)
        return 1

    data = json.loads(input_path.read_text(encoding="utf-8"))
    template = load_template(Path(__file__).resolve().parent)
    sys.stdout.write(render_prompt(data, template))
    if not template.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
