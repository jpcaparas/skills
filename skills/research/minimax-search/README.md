# minimax-search

Production skill for MiniMax's Token Plan web search API (`POST /v1/coding_plan/search`) and its quota endpoint.

## What It Covers

- A natural-language workflow: "use MiniMax search to find X" becomes focused Google-style queries, compact results, and cited answers
- Live-measured limits: at most 10 results, a 32-word effective query, a 2,048-character hard cap, and a ~52-per-minute rate limit
- Query operators that filter (`site:` once, `-site:`, quotes, `intitle:`, `after:`) and body parameters that are ignored
- Errors that arrive as HTTP 200 `base_resp` codes, including `1027` for zero results
- A zero-dependency Node helper with operator flags, throttle retries, and a quota summary

## Key Files

- `SKILL.md` - authoritative instructions
- `references/api.md` - request rules, response fields, error codes, quota, rate limits
- `references/patterns.md` - helper, `curl`, and `jq` workflows
- `references/configuration.md` - key type, region, prerequisites
- `references/gotchas.md` - quirks and failure cases
- `references/evidence.md` - dated live-probe ledger
- `scripts/search.js` - search and quota helper
- `scripts/test_helper.py` - offline helper regressions
