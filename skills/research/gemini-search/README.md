# gemini-search

Production skill for web search through Gemini's Grounding with Google Search, page reading with URL context, and a permission-gated Deep Research agent.

## What It Covers

- A natural-language workflow: "use Gemini to search X" becomes a forced-grounding Flash-Lite call with resolved, cited sources and a cost estimate
- Cost: Gemini 3+ bills every search query the model runs ($14 per 1,000 after 5,000 free per month), so the skill caps and counts queries
- Live-measured limits: 32 queries in one call, 20 URLs per read, skipped grounding, ungrounded long lists, and Deep Research at about $0.80 (standard) and $3.28 (Max)
- Quirks: redirect source links, UTF-8 byte offsets, JSON mode hiding grounding, ignored location and time filters, silent 21-URL failure
- A zero-dependency Node helper for `search`, `read`, and gated `research`

## Key Files

- `SKILL.md` - authoritative instructions
- `references/api.md` - endpoints, fields, models, prices, limits
- `references/patterns.md` - helper, `curl`, and `jq` workflows
- `references/gotchas.md` - silent failures and ignored parameters
- `references/expensive-routes.md` - gated routes and their measured costs
- `references/evidence.md` - dated live-probe ledger
- `scripts/gemini_search.js` - search, read, and research helper
- `scripts/test_helper.py` - offline helper regressions
