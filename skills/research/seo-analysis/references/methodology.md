# SEO Analysis Methodology

Use this file when the user wants a full audit from repository inspection through a fix-ready handoff prompt.

## Audit Sequence

1. Identify the delivery model.
   - Detect whether the site is SSR, SSG, ISR, CSR, or mixed.
   - Find the route map, layout system, head/metadata abstraction, and shared page templates.
   - Locate any sitemap generator, robots rules, canonical helper, structured-data helper, and image pipeline.
2. Identify page types.
   - Home page
   - Core landing pages
   - Category or collection pages
   - Product, service, or item detail pages
   - Article, docs, or resource pages
   - Paginated, filtered, or search-result pages
   - Account, cart, auth, checkout, and utility pages
3. Check rendered reality.
   - Compare source templates with rendered HTML when possible.
   - Verify what appears in the `<head>`, what content ships in HTML, and what depends on client-side execution.
4. Collect findings by root cause.
   - Shared metadata bug
   - Broken canonical strategy
   - Discovery issue caused by weak internal linking
   - Structured-data mismatch between page type and schema
   - Intentional `noindex` surfaces vs accidental exclusions
5. Produce the handoff prompt.
   - Keep it implementation-oriented.
   - Point to actual files, templates, and abstractions.
   - Include acceptance criteria and tests.

## Evidence Model

For every finding, capture:

- `severity`: blocker, high, medium, low
- `category`: crawlability, rendering, canonical, metadata, schema, content, internal-linking, performance, ai-surface
- `scope`: route pattern, page type, or component/template
- `evidence`: code path, rendered markup, response headers, or runtime observation
- `impact`: what search or preview system is affected
- `fix_direction`: the smallest safe change that addresses the root cause

Prefer evidence like:

- `app/layout.tsx` emits a single static canonical for all routes
- article pages omit `og:image`
- faceted URLs are indexable and self-canonicalize
- `robots.txt` blocks `/blog/` even though articles are linked in navigation
- page content is injected only after client fetch, leaving empty HTML shells

Avoid vague findings like:

- metadata could be better
- maybe add more schema
- AI SEO needs work

## Minimum Audit Coverage

Do not claim a “full” audit unless you checked all of these:

- indexability controls: robots meta, x-robots-tag, robots.txt, status codes
- canonicalization: rel canonical strategy, duplicate URL handling, parameter and pagination behavior
- metadata: title, meta description, OG title/description/image/url/type, site name, favicon
- discoverability: internal links, nav, breadcrumbs, XML sitemap coverage
- rendering: server HTML completeness, client-only rendering risks, hydration mismatches
- structured data: page-type alignment and JSON-LD validity
- content/template quality: uniqueness, thinness, duplication, heading structure, anchor intent
- AI-era surface readiness: preview controls, source clarity, citation-friendly structure

## Severity Guidelines

- **Blocker**: pages that should rank cannot be crawled, rendered, indexed, or canonicalized correctly.
- **High**: page types are indexable but send conflicting or systematically weak signals.
- **Medium**: supporting signals are missing, inconsistent, or suboptimal.
- **Low**: polish issues that improve resilience and previews more than core eligibility.

## Handoff Principle

The second session should not repeat the audit. Give it:

- the files to edit
- the page types affected
- the rules to preserve
- the exact acceptance checks to satisfy

Use `references/fix-prompt-spec.md` after the audit is complete.
