# Gotchas

Use this file to filter weak recommendations before they become code changes.

## AI Search Myths

1. **`llms.txt` is not required for Google Search generative AI features.** Do not add it as a Google AI Search requirement. Add one only if the project has a separate, explicit non-Google consumer and the user accepts the maintenance cost.
2. **No special AI schema is required.** Use Google-supported structured data because it matches visible content and a Search feature, not because it claims to be "GEO schema."
3. **Chunking is not mandatory.** Use clear sections for humans. Do not split content into tiny artificial blocks just for AI systems.
4. **Long-tail keyword capture is not a strategy.** Google can understand related wording; mass query-variant pages risk scaled content abuse.
5. **Fake mentions are not authority.** Do not recommend inauthentic posts, reviews, citations, or forum mentions.

## Technical Traps

1. **Robots.txt does not carry indexing directives.** If Google cannot crawl a URL, it cannot see page-level `noindex`, canonical, or structured data.
2. **JavaScript can accidentally invert indexability.** If the initial HTML has `noindex`, Google may skip rendering before JavaScript removes it.
3. **Structured data can be valid but misleading.** Rich Results Test syntax passing does not mean the schema is representative, complete, or eligible.
4. **Canonical mismatches compound.** Redirects, sitemap URLs, hreflang, internal links, and canonical tags should agree.
5. **Client-rendered content needs rendered verification.** Source HTML checks are useful, but Search and agents may depend on rendered DOM and accessibility tree output.

## Content And Policy Traps

1. **Generic content is still generic with better headings.** Improve the substance before polishing metadata.
2. **AI-assisted does not mean policy-safe.** Mass-produced content made to manipulate rankings can violate spam policies regardless of tooling.
3. **A page can be too thin even with schema.** Schema describes content; it does not replace content.
4. **Local pages can become doorway pages.** Multi-location pages need genuine location-specific information and utility.
5. **Reviews and ratings are high-risk.** Mark up only visible, genuine reviews that follow Google's feature-specific rules.

## Preview Control Traps

1. **`nosnippet` is broader than many teams expect.** It affects normal snippets and can prevent direct use as input for Google AI Overviews and AI Mode.
2. **`max-snippet:0` behaves like a hard visibility limiter.** Treat it as intentional only after confirming legal or product requirements.
3. **`data-nosnippet` requires valid HTML.** Broken markup can cause unintended snippet exclusions.
4. **Preview controls are not privacy controls.** Sensitive content should require authentication or be removed from public pages.
