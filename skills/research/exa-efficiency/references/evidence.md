# Evidence

A **2026-10-27 UTC snapshot** from one pay-as-you-go team on the default 10 QPS. It is evidence from that day, not a contract.

## What was checked, and how

- **Documentation**: `llms.txt`, about 50 `.md` doc pages (pricing, billing, search, deep search, highlights, best practices, contents, monitors, batch, Agent, Agent Ultra, Connect and its provider pages, MCP, x402, MPP, error codes, changelog, Websets, Team Management, Exa's `skill.md`), the public OpenAPI spec (`exa-spec.yaml`), the Team Management spec, and the `exa-labs/exa-mcp-server` source at `0b499f0` for MCP defaults.
- **Live calls**: REST requests against `https://api.exa.ai` with an API key: 60 billed, totalling about $1.31, plus free validation errors, failed URLs, status polls, and admin calls. The cost of record is each response's `costDollars.total` (Agent: the settled run object). Every expected figure in `scripts/test_helper.py` is one of these.
- **MCP**: keyless `web_search_exa` and `web_fetch_exa` through the hosted server.

## Measured

| Request | Billed (USD) | Notes |
| --- | --- | --- |
| search, no `type`, no contents | 0.007 | metadata only, 2 KB |
| search `lite` / `lite` + highlights | 0.004 / 0.004 | 25 KB with highlights |
| search `auto` + highlights | 0.007 | |
| search `lite` `numResults` 5 / 11 / 20 / 100 | 0.004 / 0.005 / 0.014 / 0.094 | 100 results returned |
| search `auto` `numResults` 25 / 50 + highlights | 0.022 / 0.047 | |
| search `lite` 5 results `text: true` / `text.maxCharacters: 2000` | 0.004 / 0.004 | 172 KB / 11 KB |
| search `lite` and `auto`, 5 results, text 1,000 + highlights | 0.004 / 0.007 | combining views is free |
| search `auto` + summary, 5 / 15 results | 0.012 / 0.027 | summary 0.005 / 0.015; 3.6 s / 10 s |
| search `lite` + summary; `lite` + `maxAgeHours: -1` | 0 | 400 INVALID_REQUEST_BODY |
| search `fast` / `instant` | 0.007 / 0.004 | legacy types |
| search `auto` + `maxAgeHours: 0` / `livecrawl: always` | 0.007 / 0.007 | ~9.5 s each |
| search `auto` + `extras` / `additionalQueries` / `outputSchema` text / object | 0.007 each | synthesis included |
| search `auto` + `subpages` (several shapes, also on `/contents`) | 0.007 / 0.001 | no subpages returned in 5 attempts |
| search `deep-lite` / `deep` / `deep-reasoning` | 0.012 / 0.012 / 0.015 | 1.9 s / 6.8 s / 8.5 s |
| search `deep` + `outputSchema`; `deep` + 3 `additionalQueries` | 0.012 / 0.012 | |
| search `deep` `numResults` 20 + highlights / 30 | 0.012 / 0.016 | returned 7 / 14 results: billed on returned |
| search `lite` `category: company`; `lite` `people` 30 results; `auto` `people` 5 | 0.004 / 0.024 / 0.007 | 68 KB for 30 people |
| `/contents` one page: none / highlights / text / text+highlights / summary / all three | 0.001 / 0.001 / 0.001 / 0.002 / 0.001 / 0.003 | none = full text, 45 KB |
| `/contents` 404 URL / DNS failure | 0 / 0 | `statuses[].error.tag` |
| `/contents` valid + DNS failure + `"not a url"` | 0.001 | only the valid page billed |
| `/answer` `exa`, `exa-pro`, `exa-research`, `exa-fast` | 0.005 each | `text: true` 278 KB |
| Agent `minimal` / `low` (one fact) | 0.012 / 0.025 | 3 searches each, 6–9 s |
| Agent default (unset) / `auto` + `maxCostDollars: 1` (one fact) | 0.0253 / 0.0219 | 1 search each, billed 0.006 / 0.003 |
| Agent `low` + `budget` | 0 | 400 "supported only for metered efforts" |
| Agent `auto` + `maxCostDollars: 1`, NZ dev-tool startup list ×2 | 0.6721 / 0.6806 | 148 s; 37 / 40 searches; 4.9 / 4.8 ACU; 26 rows |
| Agent `auto` cancelled after 12 s | 0 | zero usage reported after settling |
| Agent `/stop` on `auto` | 0 | 400 "supported only for ultra" |
| Batch create | 0 | 403 FEATURE_DISABLED |
| Monitor create with `example.com` webhook | 0 | 400: "cannot point to localhost, .local domains, or private IP addresses" |
| Monitor create (manual), wait 15 s, `/trigger`, list runs, delete | not reported | no run at creation; run completed in 1.8 s; run object has no cost field |
| Team Management `GET /api-keys` with the API key | 0 | 401: needs a service key |
| MCP keyless `web_search_exa` 5 results / `web_fetch_exa` | no cost shown | 8.4 KB / 3.2 KB (3,000-character default) |

## Not measured

- Monitor per-run charges (no cost field and no service key), scheduled monitors, and whether a cancelled overlapping run bills.
- Subpages billing, because no request returned subpages.
- Agent `medium`, `high`, `xhigh`, `ultra`, contact enrichment, and Exa Connect providers.
- Whether a cancelled Agent run is ever billed for accrued usage, as the docs state.
- `/responses`, `/chat/completions`, Websets, Snapshot, x402, MPP, authenticated MCP billing, and keyless MCP rate limits.
- The current SDK default for `contents`.

## Reproduce cheaply

```bash
curl -sS -X POST https://api.exa.ai/search -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" \
  -d '{"query":"postgres 18 release notes","type":"lite","numResults":11}' | jq '.costDollars'   # expect 0.005
curl -sS -X POST https://api.exa.ai/search -H "x-api-key: $EXA_API_KEY" -H "Content-Type: application/json" \
  -d '{"query":"postgres 18 release notes"}' | jq '.costDollars'                                # expect 0.007 (auto)
```

Never reproduce an uncapped `auto` or `ultra` Agent run to check its cap; use `budget.maxCostDollars: 1`.
