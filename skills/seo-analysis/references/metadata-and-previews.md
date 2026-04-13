# Metadata and Preview Audit

Use this file for title links, meta descriptions, canonical-adjacent metadata, Open Graph tags, X/social cards, favicons, site names, and preview images.

## Search Preview Checks

For each key page type, inspect:

- `<title>`
- `<meta name="description">`
- `<link rel="canonical">`
- heading alignment with the title
- favicon and site name signals

Title guidance:

- unique per page type and page instance
- descriptive before brand stuffing
- not boilerplate-heavy across the site
- not obviously stuffed with repeated keywords

Meta description guidance:

- summarize the page accurately
- differentiate template instances where needed
- avoid generic filler repeated across hundreds of pages

## Open Graph Baseline

Per the Open Graph protocol, every shareable page should have:

- `og:title`
- `og:type`
- `og:image`
- `og:url`

Usually also include:

- `og:description`
- `og:site_name`
- `og:locale`
- `og:image:alt`
- `og:image:width`
- `og:image:height`

Audit questions:

- Is `og:url` aligned with the canonical URL?
- Does every key page type get an intentional image, not the same fallback for everything?
- Are images absolute URLs and publicly reachable?
- Are OG tags emitted server-side for link unfurlers that do not execute app code deeply?

## X / Social Card Checks

Even if Open Graph is present, explicitly check:

- `twitter:card`
- `twitter:title`
- `twitter:description`
- `twitter:image`

If the stack relies on one abstraction to map search metadata and social metadata, inspect whether it actually emits both families correctly.

## Favicons and Site Names

Check:

- favicon is crawlable and stable
- favicon is not blocked in `robots.txt`
- site name signals are consistent in metadata and structured data when used
- branding is not so inconsistent that search previews alternate between names

## Image Preview Readiness

Preview quality depends on both metadata and crawlability.

Check:

- preview images are large enough and high-quality
- `max-image-preview` or other robots preview directives are not overly restrictive unless intentional
- image URLs do not require auth, cookies, or brittle signed URLs

## Common Findings

- site-wide default title overrides page-specific titles
- all pages reuse the same description
- canonical points to one URL while `og:url` points elsewhere
- social preview image is missing or relative
- article pages forget `article`-specific OG fields while marketing pages incorrectly claim `article`
- preview tags exist in components but not in the final rendered HTML
