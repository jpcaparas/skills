# synthetic-search

Production skill for Synthetic Search and the Synthetic API's `search` and `quotas` endpoints.

## What It Covers

- Live-verified `curl` calls for `POST /v2/search`
- `jq` extraction patterns for URLs, titles, and raw JSON
- `GET /v2/quotas` for current limits and usage
- A zero-dependency Node helper for readable search output
- Verified gotchas including the documented-vs-observed `published` mismatch

## Key Files

- `SKILL.md` - authoritative instructions
- `references/api.md` - endpoint reference and observed responses
- `references/configuration.md` - env var setup and prerequisite checks
- `references/patterns.md` - common workflows and helper-script usage
- `references/gotchas.md` - quirks and failure cases
- `scripts/search.js` - readable search and quota helper
- `scripts/probe_synthetic_search.py` - structured live probe helper
