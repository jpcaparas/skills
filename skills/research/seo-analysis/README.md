# SEO Analysis

Portable production skill for framework-agnostic SEO analysis of real codebases, with a built-in remediation handoff format for a second session.

## What It Covers

- crawlability, rendering, canonicals, robots directives, sitemaps, hreflang, and internal discovery
- title links, meta descriptions, OG tags, X/social cards, favicons, site names, and preview images
- structured data, JSON-LD, entity clarity, and rich-result eligibility
- content quality, duplication, information architecture, and internal linking
- AI-era search surface readiness grounded in Google’s current guidance
- deterministic prompt generation for another session to fix validated issues

## Key Files

- `SKILL.md` for the authoritative instructions
- `references/methodology.md` for the audit workflow
- `references/technical-audit.md` for crawl, render, and canonical checks
- `references/metadata-and-previews.md` for metadata and social preview checks
- `references/structured-data-and-entities.md` for schema analysis
- `references/fix-prompt-spec.md` for the second-session handoff contract
- `templates/fix-prompt-template.md` for the prompt shell
- `scripts/build_fix_prompt.py` to generate a remediation prompt from findings JSON
