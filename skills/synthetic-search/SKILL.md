---
name: synthetic-search
description: "Use Synthetic Search or the Synthetic API (`api.synthetic.new`, `SYNTHETIC_API_KEY`) for zero-data-retention web search, curl/jq examples, quota checks, and a small Node helper. Do NOT use for browser automation, crawling, or unrelated search providers."
compatibility: "Requires: `SYNTHETIC_API_KEY`; optional `jq`; Node.js 18+ for `scripts/search.js`"
---

# synthetic-search

Use Synthetic's `/v2/search` and `/v2/quotas` endpoints with verified `curl` patterns, quota checks, and a small wrapper script for readable output.

Verified against the live API on April 9, 2026. The published `skills.sh` version and an older local wrapper both informed this skill, but the instructions here prioritize observed behavior over inherited claims.

## Decision Tree

What do you need to do?

- Run a raw API call, pipe results into `jq`, or inspect the exact request/response shape
  - Read `references/api.md`

- Set up `SYNTHETIC_API_KEY`, confirm prerequisites, or decide whether to use `curl`, `jq`, or Node
  - Read `references/configuration.md`

- Use the helper script for readable search output, JSON passthrough, URL-only output, or quota summaries
  - Read `references/patterns.md`

- Debug missing `published`, blank 500 responses, fixed result counts, or auth/input failures
  - Read `references/gotchas.md`

## Quick Reference

| Task | Command | Read |
| --- | --- | --- |
| Raw search request | `curl -s https://api.synthetic.new/v2/search -H "Authorization: Bearer $SYNTHETIC_API_KEY" -H "Content-Type: application/json" -d '{"query":"rust async await"}'` | `references/api.md` |
| URLs only | `curl -s ... -d '{"query":"nix flake tutorial"}' \| jq -r '.results[].url'` | `references/patterns.md` |
| Titles with URLs | `curl -s ... -d '{"query":"python requests library documentation"}' \| jq -r '.results[] \| "\\(.title)\\t\\(.url)"'` | `references/patterns.md` |
| Human-readable search output | `node scripts/search.js "rust async await"` | `references/patterns.md` |
| Raw JSON from helper | `node scripts/search.js --json "rust async await"` | `references/patterns.md` |
| Quota summary | `node scripts/search.js quotas` | `references/api.md` |
| Structured live probe | `python3 scripts/probe_synthetic_search.py --mode all --query "rust async await"` | `references/patterns.md` |

## Reading Guide

| If the user says... | Read |
| --- | --- |
| "Use Synthetic Search on this query" | `references/api.md` |
| "Give me the best `curl` or `jq` one-liner" | `references/patterns.md` |
| "Check my Synthetic limits / quota" | `references/api.md` |
| "Why is `published` missing?" | `references/gotchas.md` |
| "How do I set up `SYNTHETIC_API_KEY` or test it?" | `references/configuration.md` |

## Verified Behaviors

1. `POST /v2/search` currently returns 5 results for a normal query in live testing.
2. Live search responses exposed `url`, `title`, and `text`; the docs and older skill versions still show a `published` field, but it was absent in verified samples.
3. `GET /v2/quotas` returned live subscription, hourly search, weekly token, and rolling-five-hour quota metadata.
4. Bad auth returned `401` with `{"error":"Invalid API Key."}`.
5. Missing `query` returned `400` with a helpful JSON error, while `{"query":""}` returned a blank-body `500`.

## Gotchas

1. **Treat `published` as optional**: Synthetic documents it and older wrappers surfaced it, but live results did not include it in testing. Write fallbacks for `null` or absent values.
2. **Display limits are local, not API-side**: the API still returned 5 results in testing; `-n` or `--limit` in `scripts/search.js` only controls what you print.
3. **Empty queries fail badly**: a missing `query` key returns a useful `400`, but an empty string currently returns `500` with no body.
4. **Quota numbers are easier to trust than docs prose**: the docs mention quota surfaces, but the live `/v2/quotas` response is the authoritative source for current numeric limits.
5. **Use raw API mode when you need precision**: the helper script is convenient, but raw `curl` plus `jq` is safer when another tool will consume the JSON directly.

## Helper Scripts

- `scripts/search.js` wraps `search` and `quotas` with zero npm dependencies.
- `scripts/probe_synthetic_search.py` runs repeatable live probes for search, quotas, and failure cases, then prints structured JSON.
- `scripts/validate.py` checks structure, frontmatter, and cross-references.
- `scripts/test_skill.py` checks eval shape and cross-reference integrity.
