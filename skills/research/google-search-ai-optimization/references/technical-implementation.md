# Technical Implementation

Use this when changing code or auditing rendered pages for Google Search and Google AI Search readiness.

## Eligibility Gate

Before copy, schema, or content recommendations, verify the page can participate in Search:

- HTTP status is `200` for canonical content, or a correct redirect for moved content.
- Primary content is visible in rendered HTML.
- Googlebot is not blocked from required HTML, CSS, JavaScript, images, or API responses needed to render the page.
- Page has no accidental `noindex`, `none`, or conflicting X-Robots-Tag header.
- Page is snippet-eligible unless restrictions are intentional.
- Canonical points to the URL that should be indexed.
- Internal links to the page use crawlable `<a href>` elements.
- Important images and videos are crawlable, descriptive, and near relevant text.

Run:

```bash
python3 scripts/audit_page.py --input https://example.com/page --expect-indexable
```

The script is a static signal probe. It does not replace rendered browser checks, Search Console URL Inspection, or Rich Results Test.

## Framework Implementation Patterns

### SSR/SSG preferred for important public pages

For public indexable pages, prefer server-rendered or statically generated HTML for primary content, title, meta description, canonical, robots directives, and JSON-LD. Client-side enhancement is fine after the indexable baseline exists.

### Metadata APIs must be page-type aware

Check the shared metadata abstraction for:

- unique title and description by route/page type
- canonical URL built from production origin and normalized path
- robots directives that default to indexable for public pages and noindex for utility/private pages
- Open Graph/social fields that do not conflict with Search metadata
- stable site name, favicon, language, and alternate locales where relevant

### JavaScript SEO checks

When the site relies on JavaScript:

- Confirm important content appears in rendered HTML.
- Avoid adding `noindex` in the original HTML if JavaScript later removes it.
- Use the History API correctly for navigable routes.
- Fingerprint JS/CSS assets for long-lived caching.
- Test lazy-loaded content and images so relevant content becomes available.
- For web components, confirm light DOM and shadow DOM content are visible in rendered HTML.

### Crawlable navigation

Use real links for discovery:

```html
<a href="/products/widget-a">Widget A</a>
```

Avoid discovery-critical navigation that depends on click handlers without `href`, form submissions, fragment-only URLs, or JavaScript pseudo-links.

## Canonicals, Duplicates, And URL Design

Use one indexable URL per primary piece of content. Canonicals should be:

- absolute URLs
- self-referential on canonical pages
- consistent with redirects, sitemap URLs, hreflang clusters, and internal links
- not blocked by robots.txt

For faceted, filtered, paginated, or sorted URLs, define which variants are indexable. Do not block a duplicate in robots.txt when Google must crawl it to see canonical or `noindex` signals.

## Structured Data

Use JSON-LD unless the existing stack has a better established pattern. Add schema only when it reflects visible page content.

Good candidates:

- `Organization` for site identity
- `BreadcrumbList` for navigational context
- `Article`, `Product`, `LocalBusiness`, `FAQPage`, `HowTo`, `VideoObject`, or other supported types only when the page actually qualifies
- `@id` values to connect related entities on the same page

Avoid:

- schema for hidden content
- reviews, ratings, prices, availability, or hours that are stale or not visible
- irrelevant schema types added only because competitors use them
- assuming schema guarantees rich results or AI Search inclusion

Validate with Rich Results Test and Search Console enhancement reports when the feature is supported.

## Robots And Preview Controls

Use the least restrictive directive that satisfies the business rule:

- `noindex`: exclude from Search results.
- `nofollow`: do not follow links on the page.
- `nosnippet`: suppress text snippet and can prevent direct use in AI Overviews and AI Mode.
- `max-snippet`: limit textual snippet length and can limit direct AI feature input.
- `max-image-preview`: control image preview size.
- `data-nosnippet`: exclude a specific visible element from snippets.

If a page should appear in AI Search features, treat accidental `nosnippet` and `max-snippet:0` as high-impact findings.

## Acceptance Checks

For each page type changed, verify:

- source and rendered HTML contain expected title, description, canonical, robots, and main content
- page can be reached through crawlable internal links
- representative images have useful alt text or are intentionally decorative
- JSON-LD parses and matches visible content
- URL Inspection or Rich Results Test confirms the expected rendered HTML for high-value pages
- Search Console is monitored after deployment for indexing, enhancement, and traffic changes
