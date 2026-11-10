# Google AI Overviews and AI Mode

## What Google says (baseline: official guidance reviewed 2026-11-10)

Source: the [AI optimization guide](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide), recorded as updated 2026-07-10 UTC, and the Search Console help pages linked below. This is a dated baseline, not a claim that policy is still current. Consult the current Google documentation when a suspected change, an uncertain rich-result eligibility, or unclear rendering or indexing affects the task, use trusted sources only to corroborate, and say so when verification is unavailable. Do not edit installed copies; propose a sourced correction.

- AI Overviews and AI Mode run on the same Search index, ranking and quality systems. For Google, AEO/GEO is SEO for the Search experience, not a separate hack track. A page must first be discoverable, crawlable, indexable and snippet-eligible.
- Query fan-out means the system may retrieve pages for related subquestions. Answer natural follow-ups on one strong page; do not create a thin page per long-tail phrase, which risks scaled content abuse.
- Content that is not commodity wins: original data, first-hand experience, decisions and tradeoffs, named sources, useful media. Do not pad for length.
- Google says none of these are required for Search generative AI features: `llms.txt` or AI text files, AI-only markup, special schema.org markup, artificial chunking, a special writing style, capturing every keyword variation, or inauthentic mentions. Add `llms.txt` only for a separate, explicit non-Google consumer the user has agreed to maintain.
- Structured data is not required for AI features. Use it only when it is page-representative, matches visible content and supports a documented Google feature; valid syntax is not eligibility, and it does not replace content.
- Preview controls: `nosnippet` and restrictive `max-snippet` (especially `0`) can stop direct use in AI Overviews and AI Mode; treat them as high-impact findings unless intentional (legal, licensing, paywall). `data-nosnippet` needs valid HTML. Preview controls are not privacy controls.
- Search Console has a per-property [Search generative AI control](https://support.google.com/webmasters/answer/16908024) under Settings, available to all sites since 2026-08-31. Properties are included by default and a child property inherits from its parent. An excluded property cannot appear in AI Overviews, AI Mode or Discover's generative features, and no on-page change fixes that, so when access is authorized, check this setting before diagnosing missing AI visibility. Exclusion is not a ranking signal for the rest of Search and does not limit model training: `Google-Extended` governs training and `noindex` governs Search as a whole. A change takes a few days to apply.
- The [Generative AI performance report](https://support.google.com/webmasters/answer/16984139) in Search Console counts impressions in AI Overviews and AI Mode by page, country, date and device. Use it as the evidence for AI visibility instead of estimating; it is missing for an excluded property.
- Indexing, ranking and serving are never guaranteed; passing checks proves eligibility signals, not selection.

## Traps specific to this work

- Multi-location pages need genuine location-specific content or they become doorway pages. Mark up only visible, genuine reviews; never fabricate ratings or cloak content.
- Mass AI-generated variations can violate spam policy regardless of tooling.
- When recording a finding, name whether a restriction such as `noindex`, `nosnippet` or JavaScript-only rendering is intentional.
