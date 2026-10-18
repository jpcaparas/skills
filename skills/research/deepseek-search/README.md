# deepseek-search

Production skill for DeepSeek's in-house web search: the Search and Fetch APIs, plus model-side search on DeepSeek models.

## What It Covers

- A natural-language workflow: "use DeepSeek search to find X" becomes short keyword queries, compact results, a few page fetches, and dated, cited answers
- Cost: $0.75 per 1,000 searches or fetches that return something; empty results and failures are free, and `count` does not change the price
- Live-measured limits: a 128-character query limit that includes operators, up to 50 results per search, and 5 requests per second per account for each API
- Quirks: dates written as midnight Beijing time, year-only `after:` excluding the whole year, `OR` floods, backslash-escaped fetch output, PDFs that cannot be fetched
- Model-side search through DeepSeek's Anthropic-format endpoint, and the controls it ignores
- A zero-dependency Node helper for search, paced batches, fetch, and a free balance check

## Key Files

- `SKILL.md` - authoritative instructions
- `references/api.md` - request and response contracts, errors, billing, rate limits
- `references/patterns.md` - helper, `curl`, and `jq` workflows
- `references/gotchas.md` - quirks and failure cases
- `references/model-search.md` - model-side web search
- `references/evidence.md` - dated live-probe ledger
- `scripts/deepseek_search.js` - search, batch, fetch, and balance helper
- `scripts/test_helper.py` - offline helper regressions
