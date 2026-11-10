---
name: seo-analysis
description: "Audit or fix real codebases for SEO: metadata, rendering, crawlability, indexability, canonicals, schema, snippets, OG/social previews, i18n, hreflang, sitemaps, robots, internal links. Also Google-grounded AEO/GEO work for AI Overviews and AI Mode, ecommerce/local details and agent browsing. Do NOT use for paid ads, rank tracking, link building or link schemes."
compatibility: "Optional: python3 for the static page probe; command-line access to the target repo, build/test tooling, browser or HTTP tooling for rendered-page verification, and Search Console, Rich Results Test or PageSpeed Insights when access is authorized."
---

# seo-analysis

Audit a codebase for search visibility risks, or implement the fixes, at the requested scope, starting from the live repository and rendered output rather than assumptions about the framework. A focused question gets a focused answer with its evidence and limits: a title fix, schema question or content edit does not need a full audit. Write files only when asked.

## How to audit

- Find the delivery model (SSR, SSG, ISR, CSR, mixed), the route map, layout and head/metadata abstractions, and the sitemap, robots, canonical, structured-data and image helpers. Review page types, not single pages: home, landing, category, detail, article/docs, paginated/filtered, and auth/account/utility. SEO failures usually come from shared template logic, so one broken helper can explain hundreds of pages. Deduplicate to root causes before prioritising.
- Verify rendered behaviour for runtime claims; SSR, hydration and edge rendering change what crawlers receive. When limited to source, label the result source-only and list the runtime checks still needed.
- Crawlability, renderability and canonicalisation come first; title tweaks do not matter if pages are blocked, duplicated or undiscoverable.
- Separate intentional exclusions from mistakes: login, cart, account, internal search, preview environments and thin utility pages are often meant to be `noindex`. Missing meta description is a preview-quality issue, not a blocker; a missing sitemap is minor on a small well-linked site; missing `hreflang` is fine for single-locale sites.
- Search titles, social titles, canonicals and schema serve different consumers; check search previews and OG/X previews separately.
- Schema must be truthful, valid and aligned with visible content. Rich-result eligibility is a separate question from validity, and "add more schema" is not a universal fix.
- AI-answer visibility is crawl access, renderable HTML, clear metadata, explicit facts and original content, plus preview controls (`nosnippet`, `data-nosnippet`, restrictive `max-snippet`) that do not suppress useful text. Do not invent AI-ranking guarantees or "AI keywords".

Each finding carries severity (blocker: pages that should rank cannot be crawled, rendered, indexed or canonicalised; high: indexable but systematically conflicting or weak signals; medium: missing or inconsistent supporting signals; low: polish), category, scope (route pattern, page type or template), evidence (code path, rendered markup, headers or runtime observation), impact and the smallest safe fix. "Metadata could be better" is not a finding. A full audit also lists which page types were and were not covered.

## Google AI Overviews and AI Mode

For Google's generative Search features, including requests phrased as AEO or GEO, read `references/google-ai-search.md` before advising or changing code. It records Google's own dated guidance: these features run on the ordinary Search index and ranking systems, so this is SEO and not a separate hack track, and `llms.txt`, AI-only markup, special schema and artificial chunking are not required. Passing checks proves eligibility signals, never selection. Comparing Search Console, Merchant Center or Business Profile data does not authorise changing those accounts; get consent first.

## Traps

- `robots.txt` disallow on a duplicate stops crawlers seeing its canonical or `noindex`; never recommend it for canonicalisation.
- Client-only metadata can look right in components and be absent from fetched HTML.
- If the initial HTML has `noindex`, Google may skip rendering before JavaScript removes it.
- Canonicals, redirects, sitemap URLs, hreflang and internal links must agree.
- Faceted navigation is often the largest silent footprint in an otherwise healthy site.
- OG images fail when URLs are relative, private, expiring or only transformed at runtime.
- Structural duplication (programmatic pages, faceted variants, token-swapped location pages) is fixed in routing, canonicals, indexing rules or template logic, not copy edits. The usual content problem is low information gain, not length.

## Fix-session handoff

Only when asked or clearly useful, give the implementing session an implementation brief: objective, repo path and stack, templates inspected, confirmed findings (severity, category, scope, evidence, desired end state), constraints (preserve intentional `noindex`, prefer shared abstraction fixes, keep search/social/canonical/schema aligned per page type), ordered work items grouped by root cause, acceptance checks in rendered HTML or generated files, and build/test commands. Name real files, include only evidence-backed findings as confirmed, and keep unverified hypotheses separate. The implementer should revalidate against the current checkout and deployment before editing. Do not hand off isolated page bugs when one helper caused them, and do not ask for copy rewrites when the issue is indexation.

## Tools and references

Dated baseline: Google Search Central and the Open Graph protocol as of April 2026. When these are stale, uncertain or conflicting, consult current Google Search Central, schema.org or protocol documentation and trusted target evidence, record the source and date, and propose a sourced correction instead of editing the installed skill.

- `python3 <skill-dir>/scripts/audit_page.py --input <url-or-file> [--expect-indexable] [--fail-on error|warning|never]` prints static signals as JSON (status, robots, canonical, JSON-LD types, crawlable links, headings). It does not render JavaScript or prove indexing; length and heading warnings are hints, not Google rules. Pass `--expect-indexable` only for pages meant to be indexed.
- `references/technical-audit.md`: crawl, rendering, canonicals, robots, sitemaps, hreflang, pagination and internal-link discovery. Read it for indexability or rendering diagnosis.
- `references/metadata-and-previews.md`: titles, descriptions, OG, X cards, favicons, site names, image previews. Read it for snippet and link-preview problems.
- `references/structured-data-and-entities.md`: JSON-LD strategy and validation priorities. Read it for schema work.
- `references/google-ai-search.md`: Google's dated guidance on AI Overviews and AI Mode, what it says is not required, and preview controls. Read it for any AEO, GEO or AI-search request.
- `references/technical-implementation.md`: eligibility gate, SSR/metadata/JS checks, canonicals, structured data, robots and preview controls, acceptance checks. Read it before changing crawl, render, metadata or schema code.
- `references/ecommerce-local-agentic.md`: product, merchant, local business and browser-agent journey checks. Read it for commerce, local or agent-readiness work.
