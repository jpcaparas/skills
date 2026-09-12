# SEO Analysis Gotchas

## False Positives

1. A missing meta description is not always a blocker. It is a preview-quality issue unless the page also has weak title or content signals.
2. A missing sitemap is not automatically catastrophic on a small well-linked site, but a polluted sitemap on a large site is a real problem.
3. A missing `hreflang` implementation is not an issue for single-locale sites.
4. `noindex` on login, cart, account, internal search, or preview environments is often correct.

## High-Value Traps

1. `robots.txt` disallow rules can block Google from seeing canonicals or rendered content on duplicates.
2. Client-only metadata generation can look correct in components while failing in fetched HTML.
3. Faceted navigation often creates the largest silent SEO footprint in otherwise healthy sites.
4. OG tags can fail because image URLs are relative, private, expiring, or transformed only at runtime.
5. A single shared layout can duplicate titles, H1s, canonicals, or schema across every route.

## AI-Era Misconceptions

1. There is no durable shortcut around helpful content, crawlability, and clear facts.
2. “Add more schema” is not a universal fix. Wrong schema can make the site less trustworthy.
3. Citation readiness depends on readable structure and explicit facts, not buzzword density.

## Handoff Mistakes

1. Do not hand another session twenty isolated page bugs when one metadata helper caused them all.
2. Do not ask for copy rewrites when the real issue is indexation or canonical duplication.
3. Do not omit acceptance checks. The implementing session needs rendered-output targets, not just source-level guesses.
