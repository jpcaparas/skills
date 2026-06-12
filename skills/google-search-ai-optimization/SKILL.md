---
name: google-search-ai-optimization
description: "Google-grounded SEO/GEO implementation for Search, AI Overviews, AI Mode, crawlability, indexability, snippets, structured data, ecommerce/local details, and agent browsing. Do NOT use for paid ads, rank tracking, non-Google directory tactics, or link schemes."
compatibility: "Requires: python3 for local static page checks. Optional: access to rendered HTML, Search Console, Rich Results Test, and PageSpeed Insights."
---

# google-search-ai-optimization

Build and audit web experiences for Google Search generative AI features using Google's official guidance as the baseline.

## Decision Tree

What are you doing?

- Implementing SEO/GEO in a codebase
  - Read `references/technical-implementation.md`
  - Run `python3 scripts/audit_page.py --input <url-or-html-file> --expect-indexable`

- Planning or editing content for AI Overviews, AI Mode, or query fan-out
  - Read `references/google-guidance.md`
  - Then read `references/content-and-entity-patterns.md`

- Working on ecommerce, local business, or agentic user journeys
  - Read `references/ecommerce-local-agentic.md`

- Debugging myths, hacks, preview controls, or questionable recommendations
  - Read `references/gotchas.md`

- Doing a broad codebase SEO audit with remediation handoff
  - Prefer {{ skill:seo-analysis }} first, then use this skill for Google AI Search-specific implementation choices.

## Quick Reference

| Task | Action | Why |
| --- | --- | --- |
| Make a page eligible for Google AI Search surfaces | Ensure it is indexable, snippet-eligible, crawlable, and useful in Google Search | Google's generative AI features are rooted in Search ranking, retrieval, and quality systems |
| Optimize for GEO/AEO on Google | Treat it as SEO, not a separate hack track | Google's guidance frames AEO/GEO work as optimizing the Search experience |
| Implement technical foundations | Use crawlable links, canonical URLs, correct status codes, rendered primary content, sitemaps, and stable metadata | Google must discover, render, understand, and select the page before content work matters |
| Improve content for AI answers | Add unique experience, original facts, clear structure, media, and user-satisfying coverage | Non-commodity, people-first content is the durable signal |
| Use structured data | Add only page-representative JSON-LD that matches visible content and Google feature docs | Structured data helps eligibility for rich results but is not required for generative AI search |
| Control snippets carefully | Use `nosnippet`, `max-snippet`, `max-image-preview`, and `data-nosnippet` only when the tradeoff is intentional | Restrictive preview controls can also limit use in AI Overviews and AI Mode |
| Ignore unsupported hacks | Do not create `llms.txt`, AI-only markup, artificial chunking, fake mentions, or mass query-variation pages for Google | Google explicitly lists these as unnecessary or risky for Google Search |
| Support browser agents | Use semantic controls, labels, stable layouts, visible actions, and clean accessibility tree signals | Agentic experiences inspect screenshots, HTML, and accessibility trees |

## Core Workflow

1. Establish the page type and business goal: informational, commercial, product, local, documentation, support, account, or utility.
2. Verify Search eligibility before optimizing copy: status code, indexability, robots directives, canonical, crawlable links, rendered main content, and snippet eligibility.
3. Inspect the rendered page and the source abstraction that creates it. Shared layout, metadata, routing, and CMS template bugs usually affect many URLs.
4. Improve the page for humans first: unique experience, non-commodity facts, clear headings, useful media, descriptive links, and satisfying next steps.
5. Add structured data only when it accurately represents visible page content and a supported Google Search feature or entity clarification.
6. For ecommerce and local sites, keep product, merchant, and business details consistent across on-page content, structured data, Merchant Center, and Google Business Profile.
7. For agentic readiness, test the journey as machine-readable UI: semantic HTML, labels, stable layout, visible actions, and no invisible overlays blocking controls.
8. Document tradeoffs. If a page uses `noindex`, `nosnippet`, JavaScript-only rendering, or duplicate templates, record whether that is intentional.

## Expected Deliverables

When using this skill, produce implementation-ready output:

- **Eligibility verdict**: indexable, snippet-eligible, crawlable, rendered, canonicalized.
- **Findings table**: severity, evidence, affected file/URL/template, Google-grounded rationale, fix.
- **Implementation plan**: ordered code changes with acceptance checks.
- **Content/entity plan**: unique facts to add, page sections to clarify, media/schema needed, internal links.
- **Myth filter**: explicitly reject AI-search hacks that Google does not support.

## Reading Guide

| Need | Read |
| --- | --- |
| Official Google AI Search guidance distilled for developers | `references/google-guidance.md` |
| Crawl, render, index, metadata, canonical, robots, JS, and schema implementation | `references/technical-implementation.md` |
| Content, entity, media, internal-link, and query fan-out patterns | `references/content-and-entity-patterns.md` |
| Ecommerce, local business, Merchant Center, Business Profile, and browser-agent UX | `references/ecommerce-local-agentic.md` |
| Unsupported tactics, edge cases, and policy traps | `references/gotchas.md` |
| Static HTML/URL signal probe | `scripts/audit_page.py` |
| Reusable implementation handoff | `templates/implementation-brief-template.md` |

## Gotchas

1. **GEO is not a separate Google hack layer**: for Google Search, optimize the search experience and foundations instead of inventing AI-only markup.
2. **Indexing and serving are never guaranteed**: passing every technical check only makes a page eligible.
3. **Preview controls affect AI features**: `nosnippet` and restrictive `max-snippet` settings can limit direct use in AI Overviews and AI Mode.
4. **Structured data is not a generative AI requirement**: use it because it accurately describes visible content and supports rich-result eligibility.
5. **Do not scale pages for every fan-out query**: mass pages for query variants can become scaled content abuse.
6. **Rendered reality wins**: framework metadata APIs, client rendering, web components, and hydration can change what Google and agents actually see.

## Source Baseline

This skill is grounded in official Google guidance current as of May 16, 2026, especially Google's "Optimizing your website for generative AI features on Google Search" guide, last updated 2026-05-15 UTC. Re-check the source when Google changes Search AI feature guidance, preview controls, or structured data policies.

## Helper Files

- `references/README.md` - source map and disclosure guide.
- `references/google-guidance.md` - official Google AI Search guidance, reframed for web development.
- `references/technical-implementation.md` - implementation checks and framework patterns.
- `references/content-and-entity-patterns.md` - durable content and entity strategies.
- `references/ecommerce-local-agentic.md` - commerce, local, and browser-agent readiness.
- `references/gotchas.md` - traps, myths, and false positives.
- `scripts/audit_page.py` - deterministic static signal audit for one URL or HTML file.
- `scripts/validate.py` - structural validator for this skill.
- `scripts/test_skill.py` - lightweight regression tests for packaging and audit behavior.
- `templates/implementation-brief-template.md` - fix-ready planning template.
