# Evidence ledger

All probes ran on 2026-10-19 (UTC) from one Amp orb against a billed Gemini API project on a high usage tier, through generateContent and the Interactions API. They ran roughly 400-500 search queries outside the agents. Those were probably inside the 5,000 free monthly queries; at list price they would be about $6-7. Token costs outside the agents were under $0.30, and the two Deep Research runs came to about $4.10. Spend is estimated from list prices because the API does not report it.

## What was measured

| Area | Probe | Result |
| --- | --- | --- |
| Model availability | One fact question on eight models | 2.5 Flash and Flash-Lite: 404 for new users. 3.1 and 3.5 Flash-Lite, 3.6 and 3.8 Flash, 3.1 Pro, 4 Argon: same correct answer; 2.2-17.9 s; 1-2 queries |
| Token accounting | Grounded calls | Search content not counted (24-token prompts); URL context content counted as `toolUsePromptTokenCount` |
| Source links | Chunks and Interactions annotations | Redirect links titled by domain; `HEAD` reveals `Location`; links resolved after an hour; chunks repeat |
| Billing counter | Interactions `usage.grounding_tool_count` | Matches executed queries |
| Skipping search | Repeats, trivial prompts, thinking levels, large lists | 1 of 5 default runs skipped; trivial prompts 0 queries; Flash-Lite `high` thinking 0 queries in 3 of 3 runs; 50-entity list 0 queries |
| Forcing search | "Ground every answer... always search first" system instruction | 5 of 5 searched; 24 of 24 across eight questions and three models |
| Query caps | Caps of 1 and 3 by system instruction | Flash-Lite 4 → 1 with a cap of 1; 23 of 24 runs within a cap of 3; 3.8 Flash ignored a cap of 1 |
| Fan-out ceiling | 20, 50, and 100 entities in one call | 20-25 queries for 20; 1, 29, or 32 for 50 depending on model; 15 for 100, with 85 lines ungrounded |
| Default choice | Eight questions × three models, forced, cap 3 | 3.1 Flash-Lite 13 queries, 3.5 s mean; 3.5 Flash-Lite 16, 3.4 s; 3.8 Flash 17, 10.8 s, about 8x token cost |
| Operators and filters | `site:` in prompt; `excludeDomains`; `timeRangeFilter`; `retrievalConfig` | `site:` restricted every source; `excludeDomains` 400; `timeRangeFilter` accepted, no effect; location and language no visible effect |
| Support offsets | Answer with ü and € | Offsets match UTF-8 bytes (2 of 2), not characters (0 of 2) |
| Structured output | `responseSchema` on generateContent; `response_format` on Interactions | generateContent dropped grounding metadata while still searching; Interactions kept it but ran 6 queries uncapped (1 and 4 with a cap of 2) |
| URL context | HTML, PDF, plain text, JSON, image, SPA, YouTube, 404, localhost, NXDOMAIN, 20 and 21 URLs | As in `references/gotchas.md`; 21 URLs failed every URL silently |
| Combined tools | Search plus URL context with "read it" | Searched, never read |
| Storage | Interactions default, `store: false`, delete | Stored by default; `store: false` returned no ID; delete then GET returned 404 |
| Streaming | `streamGenerateContent?alt=sse` | Metadata only in the final event |
| Rate limits | 60 and 250 concurrent trivial calls; 30 concurrent grounded calls | No 429s on this tier |
| Deep Research | Standard and Max on the same brief | As in `references/expensive-routes.md` |

## Untested or unverified

- Which model Deep Research bills its tokens at, and whether its searches count against the 5,000 free queries.
- Actual invoiced spend (the API exposes none).
- Free-tier behaviour (most Gemini 3 models list grounding as unavailable on the free tier).
- Rate-limit thresholds on lower tiers and the spend-based 429.
- `URL_RETRIEVAL_STATUS_UNSAFE` (no URL triggered it).
- Grounding with Google Maps, File Search, and Live API grounding.

## Rerun probes

Each costs a few cents at most after the free tier; none prints the key.

```bash
H=scripts/gemini_search.js
node $H search --json "What changed in PostgreSQL 18.6?" | jq '{grounded, queries, coverage, estimated_cost_usd}'
node $H search --json --model gemini-3.8-flash "Latest stable Go release and date" | jq '{model, queries}'
node $H read --json --ask "Release date?" https://www.postgresql.org/docs/18/release-18-6.html | jq '{urls, page_tokens}'
curl -sS "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"hi"}]}]}' | jq .error.message      # still retired for new users?
curl -sS "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200" -H "x-goog-api-key: $GEMINI_API_KEY" |
  jq -r '.models[].name' | grep -E 'flash-lite|flash$|pro|argon'      # new default candidates?
```

When a new Flash-Lite model appears, rerun the eight-question comparison (forced grounding, cap 3) before changing the default. Update `references/api.md`, `references/gotchas.md`, the helper's price table, and this file in the canonical repository with the date and evidence.
