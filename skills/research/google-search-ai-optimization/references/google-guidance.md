# Google Guidance For AI Search

This file distills Google's official guidance for generative AI features on Google Search into developer decisions.

## Core Model

Google says SEO remains relevant for generative AI search because AI Overviews and AI Mode are built on the same Search index, ranking, and quality systems. The important implications are:

- A page must first be discoverable, crawlable, indexable, and eligible to appear in Google Search.
- Content quality matters more than AI-specific formatting.
- Retrieval-augmented generation depends on relevant, up-to-date pages from the Search index.
- Query fan-out can retrieve pages that answer related subquestions even when the page does not exactly match the user's original wording.
- For Google Search, AEO and GEO are best treated as SEO for the Search experience, not a separate set of hacks.

## Developer Priorities

1. **Make the page eligible**: valid status, crawl access, rendered main content, sensible canonical, no accidental `noindex`, and snippet eligibility when you want AI Search visibility.
2. **Make the page useful**: original experience, expert detail, clear facts, satisfying answers, and media that helps the user.
3. **Make the page understandable**: clear headings, descriptive titles, useful internal links, alt text, stable page purpose, and structured data when it represents visible content.
4. **Make the page trustworthy to maintain**: avoid template duplication, stale structured data, fake reviews, hidden schema, and mass AI-generated variations.

## What "Non-Commodity" Means In Practice

Non-commodity content goes beyond generic summaries. For a development task, ask what data, experience, or evidence the site can show that another generic page cannot:

- original measurements, benchmarks, pricing, availability, or field data
- first-hand reviews, decisions, tradeoffs, and outcomes
- product/service details that help a user choose or complete a task
- named people, organizations, locations, dates, and sources where appropriate
- useful media: diagrams, screenshots, product photos, video, comparison tables, transcripts, or annotated examples

Do not turn this into forced length. A concise page can be excellent when it fully satisfies the user's need.

## Query Fan-Out Without Scaled Abuse

Query fan-out means AI systems may explore related questions to answer a broader user need. Use this to improve one strong page, not to generate many weak pages.

Good pattern:

- Add sections that answer natural follow-up questions on the same topic.
- Use headings users can scan.
- Add internal links to deeper pages only when those pages have distinct value.
- Use the words users actually use, but keep the writing natural.

Bad pattern:

- Create one thin page for every long-tail phrase.
- Rewrite the same content with tiny keyword substitutions.
- Create AI-only content that humans would not find satisfying.
- Hide or overload text to manipulate generated answers.

## Myths Google Explicitly Defuses

For Google Search generative AI features, do not require:

- `llms.txt` or special AI text files
- AI-only machine-readable markup
- artificial chunking of content into tiny answer blocks
- writing in a special style only for AI systems
- capturing every long-tail keyword variation
- inauthentic mentions across the web
- special schema.org markup for generative AI search

## Snippets And AI Search

Snippet controls matter more in the AI Search era because restrictive preview controls can affect direct use in AI Overviews and AI Mode. If the business wants visibility in these features, avoid accidental `nosnippet` or overly restrictive `max-snippet` settings on valuable pages.

Use preview controls intentionally for legal, privacy, licensing, paywall, or product strategy reasons. Document the tradeoff in the finding rather than treating every restriction as a bug.

## When To Re-Verify

Re-open the official docs before making strong claims when:

- Google changes AI Overviews, AI Mode, preview control behavior, or structured data policies.
- The recommendation depends on a specific rich result type.
- The site uses JavaScript rendering, web components, faceted navigation, or user-generated content.
- The user asks for "latest", "official", "current", or policy-sensitive guidance.
