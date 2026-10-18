# synthetic-search

Production skill for Synthetic's zero-data-retention web search API (`POST /v2/search`) and its `GET /v2/quotas` endpoint.

## What It Covers

- A natural-language workflow: "use Synthetic search to find X" becomes focused queries, compact results, and cited answers
- Live-measured limits: 5 results per search, a 4,096-character effective query, a 100,000-character hard cap, 250 searches per hour on the tested account
- Query operators that work (`site:`, `-site:`) and body parameters that are silently ignored
- The undocumented `highlights` field, optional `published`, and full-page `text`
- A zero-dependency Node helper that blocks requests the API would mishandle while still charging quota
- A live probe for re-verifying limits, plus offline helper tests

## Key Files

- `SKILL.md` - authoritative instructions
- `references/api.md` - request rules, response fields, errors, quota semantics
- `references/patterns.md` - helper, `curl`, and `jq` workflows
- `references/configuration.md` - key setup and prerequisites
- `references/gotchas.md` - quirks and failure cases
- `references/evidence.md` - dated live-probe ledger
- `scripts/search.js` - search and quota helper
- `scripts/probe_synthetic_search.py` - live re-verification probe
- `scripts/test_helper.py` - offline helper regressions
