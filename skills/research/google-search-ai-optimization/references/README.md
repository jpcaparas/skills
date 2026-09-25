# Google Search AI Optimization References

Use these references progressively. Load only the file that matches the work in front of you.

## Source Map

The recorded May 16, 2026 baseline is Google's "Optimizing your website for generative AI features on Google Search" guide, recorded as updated 2026-05-15 UTC. It is not a perpetual freshness claim. Supporting guidance comes from Google Search Essentials, the SEO Starter Guide, JavaScript SEO, robots meta specifications, structured data documentation, ecommerce guidance, LocalBusiness structured data, and Google's linked web.dev article on agent-friendly websites. Source URLs are listed in `metadata.json`; refresh the relevant official source when uncertainty or change affects the task.

## Files

| File | Load when |
| --- | --- |
| `references/google-guidance.md` | You need the official Google AI Search model, priorities, and myths |
| `references/technical-implementation.md` | You are changing code, rendering, metadata, crawl/index controls, or schema |
| `references/content-and-entity-patterns.md` | You are planning or revising content for Search and AI answers |
| `references/ecommerce-local-agentic.md` | You are optimizing products, local businesses, or browser-agent journeys |
| `references/gotchas.md` | You need to filter false positives, unsupported tactics, or policy risks |

## Validation Flow

1. Select checks that test the requested change. For static signals, use `python3 scripts/audit_page.py --input <url-or-file>`; add `--expect-indexable` only for pages intended to be indexed.
2. Use rendered checks and official Google tools when the question needs them and access is authorized: URL Inspection, Rich Results Test, Search Console reports, and PageSpeed Insights.
3. Distinguish observed evidence from unverified eligibility. The probe neither renders JavaScript nor proves Google indexing; a scoped edit does not require a site-wide audit.
