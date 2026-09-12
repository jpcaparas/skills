#!/usr/bin/env python3
"""
probe_seo_analysis.py — Deterministic regression checks for the seo-analysis skill.
"""

from __future__ import annotations

from pathlib import Path

import build_fix_prompt


def run_suite() -> dict:
    template = (Path(__file__).resolve().parent.parent / "templates" / "fix-prompt-template.md").read_text(encoding="utf-8")
    sample = {
        "objective": "Fix validated SEO issues for marketing pages.",
        "repo": "/tmp/example-repo",
        "stack": "Mixed SSR app",
        "pages_or_templates": ["app/layout.tsx", "app/blog/[slug]/page.tsx"],
        "verification_commands": ["pnpm build", "pnpm test"],
        "findings": [
            {
                "severity": "high",
                "category": "metadata",
                "scope": "blog article pages",
                "evidence": "The metadata helper emits one static title and description.",
                "fix_direction": "Generate title and description from article data while preserving brand suffix logic."
            },
            {
                "severity": "blocker",
                "category": "crawlability",
                "scope": "docs pages",
                "evidence": "robots meta is set to noindex on all docs routes.",
                "fix_direction": "Limit noindex to preview routes and allow production docs pages to be indexed."
            }
        ]
    }

    normalized = build_fix_prompt.normalize_findings(sample["findings"])
    prompt = build_fix_prompt.render_prompt(sample, template)
    checks = [
        ("severity-order", normalized[0]["severity"] == "blocker"),
        ("prompt-objective", "Fix validated SEO issues for marketing pages." in prompt),
        ("prompt-findings", "[BLOCKER] crawlability | docs pages" in prompt),
        ("prompt-acceptance", "blog article pages" in prompt and "docs pages" in prompt),
        ("prompt-verification", "- pnpm build" in prompt and "- pnpm test" in prompt),
    ]
    passed = sum(1 for _name, ok in checks if ok)
    return {
        "passed": passed == len(checks),
        "summary": {"checks_total": len(checks), "checks_passed": passed},
        "checks": [{"name": name, "passed": ok} for name, ok in checks],
    }


def main() -> int:
    suite = run_suite()
    for item in suite["checks"]:
        status = "PASS" if item["passed"] else "FAIL"
        print(f"{status}: {item['name']}")
    print(
        f"\nSummary: {suite['summary']['checks_passed']}/{suite['summary']['checks_total']} checks passed"
    )
    return 0 if suite["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
