---
name: google-search-ai-optimization
description: "Google-grounded SEO/GEO implementation for Search, AI Overviews, AI Mode, crawlability, indexability, snippets, structured data, ecommerce/local details, and agent browsing. Do NOT use for paid ads, rank tracking, non-Google directory tactics, or link schemes."
compatibility: "Optional: python3 for the static page probe; rendered HTML, Search Console, Rich Results Test and PageSpeed Insights when access is authorized."
---

# google-search-ai-optimization

Implement and audit for Google's generative AI search features using Google's own guidance as the baseline. Match scope to the request: a title fix, schema question or content edit does not need a full audit. For a broad codebase SEO audit with a fix handoff, start with `seo-analysis`, then use this skill for Google AI Search choices.

## What Google says (baseline: official guidance reviewed 2026-05-16)

Source: the [AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), recorded as updated 2026-05-15 UTC. This is a dated baseline, not a claim that policy is still current. Consult the current Google documentation when a suspected change, an uncertain rich-result eligibility, or unclear rendering or indexing affects the task, use trusted sources only to corroborate, and say so when verification is unavailable. Do not edit installed copies; propose a sourced correction.

- AI Overviews and AI Mode run on the same Search index, ranking and quality systems. For Google, AEO/GEO is SEO for the Search experience, not a separate hack track. A page must first be discoverable, crawlable, indexable and snippet-eligible.
- Query fan-out means the system may retrieve pages for related subquestions. Answer natural follow-ups on one strong page; do not create a thin page per long-tail phrase, which risks scaled content abuse.
- Content that is not commodity wins: original data, first-hand experience, decisions and tradeoffs, named sources, useful media. Do not pad for length.
- Google says none of these are required for Search generative AI features: `llms.txt` or AI text files, AI-only markup, special schema.org markup, artificial chunking, a special writing style, capturing every keyword variation, or inauthentic mentions. Add `llms.txt` only for a separate, explicit non-Google consumer the user has agreed to maintain.
- Structured data is not required for AI features. Use it only when it is page-representative, matches visible content and supports a documented Google feature; valid syntax is not eligibility, and it does not replace content.
- Preview controls: `nosnippet` and restrictive `max-snippet` (especially `0`) can stop direct use in AI Overviews and AI Mode; treat them as high-impact findings unless intentional (legal, licensing, paywall). `data-nosnippet` needs valid HTML. Preview controls are not privacy controls.
- Indexing, ranking and serving are never guaranteed; passing checks proves eligibility signals, not selection.

## Traps

- robots.txt carries no indexing directives: if Googlebot cannot crawl a URL it never sees page-level `noindex`, canonical or structured data. Do not block a duplicate that must be crawled to see its canonical.
- If the initial HTML has `noindex`, Google may skip rendering before JavaScript removes it.
- Canonicals, redirects, sitemap URLs, hreflang and internal links must agree.
- Client-rendered content, framework metadata APIs, web components and hydration change what Google and agents see; verify rendered output, not just source.
- Preserve intentional exclusions (`noindex` utility pages, private routes). Pass `--expect-indexable` to the probe only for pages meant to be indexed.
- Multi-location pages need genuine location-specific content or they become doorway pages. Mark up only visible, genuine reviews; never fabricate ratings or cloak content.
- Comparing Search Console, Merchant Center or Business Profile data does not authorize changing those accounts; get consent first.
- Mass AI-generated variations can violate spam policy regardless of tooling.

## Tools and references

- `python3 <skill-dir>/scripts/audit_page.py --input <url-or-file> [--expect-indexable] [--fail-on error|warning|never]` prints static signals as JSON (status, robots, canonical, JSON-LD types, crawlable links, headings). It does not render JavaScript or prove indexing; length and heading warnings are hints, not Google rules.
- `references/technical-implementation.md`: eligibility gate, SSR/metadata/JS checks, canonicals, structured data, robots and preview controls, acceptance checks. Read it before changing crawl, render, metadata or schema code.
- `references/ecommerce-local-agentic.md`: product, merchant, local business and browser-agent journey checks. Read it for commerce, local or agent-readiness work.

When recording a finding, name whether a restriction such as `noindex`, `nosnippet` or JavaScript-only rendering is intentional.
