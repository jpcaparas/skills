# Evidence

A **2026-10-18 UTC snapshot** from one Standard-plan account (100,000 plan credits, `maxConcurrency` 50). It is evidence from that day, not a contract. Each call was made against `https://api.firecrawl.dev/v2`; the cost is the response's `creditsUsed` (or the job status's `creditsUsed`), cross-checked against `GET /team/credit-usage` before and after. A monitor was spending on the same account, so balance deltas were noisy and the reported `creditsUsed` is the figure of record.

Test targets were `books.toscrape.com` (a public scraping sandbox), `httpbin.org` status pages, `example.com`, `docs.firecrawl.dev`, and an arXiv PDF. No premium or provider-routed host was sent, and `/agent` and `/extract` were never called.

## Measured

| Request | Billed | Notes |
| --- | --- | --- |
| `GET /team/credit-usage` ×4, `/team/queue-status`, `/crawl/active`, `/monitor`, crawl status ×6, `/crawl/{id}/errors` | 0 | |
| scrape markdown, cache hit | 1 | `cacheState: "hit"`, 0.3 s |
| same, `maxAge: 0` | 1 | 1.0 s |
| scrape of a 404 page / a 500 page | 1 / 1 | `metadata.statusCode` 404 / 500 |
| scrape of an unresolvable domain | 0 | DNS error |
| scrape timing out (`timeout: 5000` on a 10 s page) | 0 | HTTP 408 |
| map, `limit: 5000` on docs.firecrawl.dev | 1 | 1,612 URLs |
| search `limit` 3 / 10 / 11 | 2 / 2 / 4 | results 3 / 10 / 11 |
| search `limit: 5`, `sources: [web, news]` | 2 | 10 results |
| search `limit: 2` + `scrapeOptions` markdown | 4 | |
| search feedback (`rating: good`, one valuable source) | −1 | `dailyRefundCap: 100` |
| formats `links`, `images`, `html`+`rawHtml`, `screenshot`, full-page screenshot, `summary`, `branding`, `markdown`+`changeTracking` | 1 each | |
| format `json` / `markdown`+`summary`+`json` | 5 / 5 | |
| 15-page PDF: default parsers / `maxPages: 2` / `parsers: []` | 15 / 2 / 1 | `[]` returned 2.9 MB of base64 in `markdown` |
| crawl `limit: 5` | 5 | |
| crawl `limit: 40`, `DELETE` after 4 s | 40 | already completed when cancelled |
| **crawl `example.com`, `limit: 50000`, defaults** | **809** | 809 query-string variants of one page; accepted on a ~3,000-credit balance; finished before the cancel arrived |
| crawl `example.com`, `limit: 3` + `ignoreQueryParameters: true` / + `sitemap: "skip"` / both | 1 / 1 / 1 | |
| batch scrape of one page + one 404 | 2 | |
| batch scrape containing a malformed URL | 0 | whole batch rejected with HTTP 400 |

Total spend: 3,087 → 2,169 credits, of which 809 was the example.com crawl. That crawl was a mistake in the spike itself. It is why the guard warns on any crawl without `ignoreQueryParameters: true` or `sitemap: "skip"`, and why `SKILL.md` tells agents to pass `--budget`, which would have blocked it.

## Reproduce cheaply

```bash
G="python3 <skill-dir>/scripts/firecrawl_guard.py"
$G balance
curl -sS -X POST https://api.firecrawl.dev/v2/scrape -H "Authorization: Bearer $FIRECRAWL_API_KEY" -H "Content-Type: application/json" \
  -d '{"url":"https://books.toscrape.com/","formats":["markdown"]}' | jq '.data.metadata | {creditsUsed, cacheState}'
curl -sS -X POST https://api.firecrawl.dev/v2/search -H "Authorization: Bearer $FIRECRAWL_API_KEY" -H "Content-Type: application/json" \
  -d '{"query":"firecrawl map endpoint","limit":11}' | jq .creditsUsed     # expect 4
```

Never reproduce the 809-credit crawl. To check crawl scope cheaply, crawl with `limit: 3` and inspect the returned `sourceURL`s.

## Not tested

- `/agent` and `/extract` (banned), interact sessions, monitor creation, ZDR, `redactPII`, `checkPromptInjection`, `lockdown`, change-tracking `json` mode, `/parse` uploads, DOCX/XLSX parsing, developer search, Research Index billing, webhooks.
- Whether a crawl without `limit` on a small balance returns 402, and how pay-as-you-go behaves at zero (deliberately not triggered).
- Rate-limit enforcement and which limit batch scrape shares.
