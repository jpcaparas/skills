# Technical SEO Audit

Use this file for crawlability, rendering, canonicals, robots directives, sitemaps, hreflang, pagination, and internal discovery.

## Crawlability and Indexability

Check these first:

1. HTTP status codes
   - Important pages must return `200`.
   - True removals should return `404` or `410`, not soft-404 content inside `200`.
2. `robots.txt`
   - Use it for crawl control, not canonicalization.
   - Verify it does not block templates or asset paths needed for rendering.
3. Page-level directives
   - Check `<meta name="robots">` and `X-Robots-Tag`.
   - Distinguish deliberate exclusions from mistakes.
4. Canonical targets
   - Important indexable pages should self-canonicalize or point intentionally to a preferred equivalent.
   - Canonicals should resolve and be indexable.

## Rendering and Discovery

Modern stacks fail SEO when HTML ships as a shell.

Check:

- whether core body copy is present in initial HTML
- whether links are real anchor tags with crawlable `href` values
- whether route changes rely on fragment URLs instead of proper paths
- whether metadata is injected only after client boot
- whether lazy loaders or gated fetches hide primary content from initial render

Red flags:

- `<div id="app"></div>` with no meaningful text
- product, article, or docs content fetched only in the browser
- internal navigation implemented with click handlers but no anchor tags
- canonicals or titles generated client-side only

## Canonical Strategy

Audit canonicals at the page-type level:

- home page
- category/collection pages
- detail pages
- paginated pages
- faceted/filter pages
- parameterized tracking URLs
- alternate language versions

Questions:

- Is each page choosing its own canonical or inheriting a broken site-wide default?
- Are filtered or sorted variants canonicalized to a clean base when they should not be indexed?
- Are paginated pages self-canonicalizing, or collapsing incorrectly onto page 1?
- Do protocol, host, slash, and casing variants normalize consistently?

## Sitemaps

Check:

- sitemap exists and is referenced in `robots.txt`
- only canonical, index-worthy URLs are included
- excluded, redirected, `noindex`, blocked, and duplicate URLs are not present
- large sites split sitemaps sanely by type or volume

Remember:

- XML sitemap `priority` and `changefreq` do not matter to Google
- sitemap inclusion does not override `noindex`, bad canonicals, or blocked crawling

## Hreflang and Internationalization

When the site has locales or regional variants:

- verify each alternate references all siblings, including itself
- verify canonical and hreflang do not contradict each other
- verify locale pages are not folded into one canonical accidentally
- verify locale-specific OG locale tags when relevant

Do not recommend hreflang when the site is single-locale.

## Internal Linking and Discovery

Important pages should be discoverable from crawlable links, not only search boxes, JS events, or XML sitemaps.

Check:

- global nav and footer
- breadcrumbs
- contextual links inside content
- HTML pagination links
- hub pages and related-item blocks
- orphaned templates that exist but are not linked internally

Weak internal-link signals often explain why pages are crawled rarely even when technically indexable.

## Acceptance Checks

Use these when drafting remediation work:

- every intended page type returns the right status code and directives
- important URLs render meaningful primary content in server HTML
- canonicals are correct per page type
- sitemaps contain canonical index-worthy URLs only
- internal links are crawlable anchors
- international alternates are consistent where applicable
