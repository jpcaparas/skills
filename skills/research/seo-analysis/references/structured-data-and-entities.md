# Structured Data and Entities

Use this file when the issue involves JSON-LD, schema selection, rich result eligibility, or weak entity clarity.

## Principles

1. Match schema to the real page purpose.
2. Prefer valid, specific, supportable types over stuffing many irrelevant types.
3. Keep structured data consistent with visible content.
4. Treat JSON-LD as a support signal, not a substitute for poor page content.

## Page-Type Mapping

Common pairings:

- organization or business home page -> `Organization` or `LocalBusiness` when appropriate
- article/resource page -> `Article`, `NewsArticle`, or `BlogPosting` when it truly fits
- product detail page -> `Product` plus offer/review data only when the content supports it
- breadcrumbed navigational hierarchies -> `BreadcrumbList`
- FAQ content -> `FAQPage` only when the page visibly presents actual questions and answers

Be conservative. Unsupported or misleading schema is worse than missing schema.

## Audit Checks

- JSON-LD is emitted in rendered HTML, not just assembled in runtime objects
- page type and schema type agree
- required fields for the chosen type are present when needed
- URLs inside schema are canonical and resolve
- image URLs are valid and publicly fetchable
- organization data is consistent across templates
- breadcrumbs match actual navigational hierarchy

## Entity Clarity

For organizations, people, products, and authored content, check whether the site makes entities explicit through:

- clear names and headings
- author or publisher identification where relevant
- consistent brand naming
- explicit publication and modification dates when meaningful
- structured data that aligns with visible facts

## Common Anti-Patterns

- injecting a giant generic `WebSite` blob everywhere and calling it done
- using `FAQPage` for accordion marketing fluff
- publishing `Product` schema on category pages
- putting review or rating fields in schema without visible support on the page
- shipping invalid JSON-LD because of template interpolation bugs

## Acceptance Checks

- each major page type has at most the schema it can justify
- schema fields match visible page content
- breadcrumbs and organization data are internally consistent
- no invalid, contradictory, or clearly spammy schema remains
