# Google Search AI Optimization References

Use these references progressively. Load only the file that matches the work in front of you.

## Source Map

The canonical baseline is Google's "Optimizing your website for generative AI features on Google Search" guide, last updated 2026-05-15 UTC. Supporting implementation guidance comes from Google Search Essentials, the SEO Starter Guide, JavaScript SEO, robots meta specifications, structured data documentation, ecommerce guidance, LocalBusiness structured data, and Google's linked web.dev article on agent-friendly websites.

## Files

| File | Load when |
| --- | --- |
| `references/google-guidance.md` | You need the official Google AI Search model, priorities, and myths |
| `references/technical-implementation.md` | You are changing code, rendering, metadata, crawl/index controls, or schema |
| `references/content-and-entity-patterns.md` | You are planning or revising content for Search and AI answers |
| `references/ecommerce-local-agentic.md` | You are optimizing products, local businesses, or browser-agent journeys |
| `references/gotchas.md` | You need to filter false positives, unsupported tactics, or policy risks |

## Validation Flow

1. Run `python3 scripts/audit_page.py --input <url-or-file> --expect-indexable` for representative pages.
2. Use official Google tools for final validation when applicable: URL Inspection, Rich Results Test, Search Console reports, and PageSpeed Insights.
3. Capture evidence from source files, rendered HTML, and tool output before recommending fixes.
