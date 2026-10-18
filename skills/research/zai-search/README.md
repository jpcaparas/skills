# zai-search

Production skill for Z.ai's search tools: web search, web reader, and Zread GitHub repository search, over MCP (Coding Plan quota) or the billed REST API.

## What It Covers

- A natural-language workflow: "use Z.ai search to find X" becomes short queries, compact results, page reads, and cited answers
- Which budget each route spends: MCP calls use the Coding Plan's tool quota; REST costs $0.01 per search or read (about $0.0015 for `search_std`) on the tested key
- Live-measured limits: about 10 results per search-prime query, ~40 for `search_std`, a `1302` throttle at eight concurrent MCP calls, and free throttled calls
- Quirks: rewritten queries, `site:` as a ranking hint, ignored domain and size filters, missing dates on MCP results, double-encoded JSON, and the MCP session handshake
- A zero-dependency Node helper for search, read, Zread, and a free quota and balance summary

## Key Files

- `SKILL.md` - authoritative instructions
- `references/api.md` - MCP and REST contracts, errors, billing, rate limits
- `references/patterns.md` - helper, MCP `curl`, and `jq` workflows
- `references/configuration.md` - key types, plans, hosts, MCP client setup
- `references/gotchas.md` - quirks and failure cases
- `references/evidence.md` - dated live-probe ledger
- `scripts/zai.js` - search, reader, Zread, and quota helper
- `scripts/test_helper.py` - offline helper regressions
