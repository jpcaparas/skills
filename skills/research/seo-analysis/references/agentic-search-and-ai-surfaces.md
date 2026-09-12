# AI-Era Search and Answer Surfaces

Use this file when the user asks about AI Overviews, answer engines, citation readiness, or “agentic SEO.”

## Ground Rule

Do not invent a separate mystical SEO system for AI answers.

The durable inputs are still:

- crawl access
- renderable HTML
- canonical clarity
- strong page-level facts
- high-quality original content
- structured data that matches the page
- preview controls that do not accidentally suppress useful snippets or images

Google’s current guidance for AI features points back to the same crawl, indexing, and preview controls already used for Search.

## What to Audit

1. Source clarity
   - Can a system quickly understand what the page is about, who published it, and which entity it refers to?
2. Answer extraction
   - Does the page present key facts, steps, definitions, and comparisons in explicit language rather than only buried in decorative UI?
3. Citation readiness
   - Are headings, tables, lists, dates, authors, and entity names clear enough to quote or summarize accurately?
4. Preview controls
   - Are `nosnippet`, `data-nosnippet`, or restrictive preview directives suppressing useful text or images unintentionally?
5. Crawl/render readiness
   - Is the content available in HTML and not trapped behind client-only interactions?

## Practical Recommendations

- prefer semantic HTML and explicit headings over UI-only composition
- keep factual blocks close to their headings
- expose authorship, publish/update dates, and organization details when relevant
- use schema to reinforce, not replace, visible facts
- avoid hiding essential text in tabs or accordions that ship empty HTML initially

## What Not to Recommend

- fake “AI keywords”
- schema stuffing unrelated types to chase overviews
- speculative hidden text or cloaking tactics
- disabling snippets globally unless the user explicitly wants less visibility

## When Preferred Sources Matters

If the publisher wants stronger visibility for a designated publication or profile in evolving Google surfaces, inspect whether their site supports clear source identity and whether any relevant preferred-source guidance applies. Treat it as supplemental, not a substitute for core technical hygiene.
