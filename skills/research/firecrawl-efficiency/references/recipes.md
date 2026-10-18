# Cheap Routes, Copy-Ready

Each recipe is the lowest-credit way to do one job. Run the guard on any body before sending it:

```bash
G="python3 <skill-dir>/scripts/firecrawl_guard.py"
$G estimate crawl body.json --budget 100   # exit 0 ok, 2 warn, 3 blocked
$G balance                                 # free
```

The REST examples assume:

```bash
FC=https://api.firecrawl.dev/v2
AUTH="Authorization: Bearer $FIRECRAWL_API_KEY"
JSON="Content-Type: application/json"
```

Always write responses to a file and read fields with `jq`; never paste a raw response into context.

## Table of Contents

- [Read one page](#read-one-page)
- [Find pages, then read the best ones](#find-pages-then-read-the-best-ones)
- [Pull a section of a site](#pull-a-section-of-a-site)
- [Crawl when links must be followed](#crawl-when-links-must-be-followed)
- [Structured fields](#structured-fields)
- [PDFs](#pdfs)
- [Interactive pages](#interactive-pages)
- [Monitors](#monitors)
- [MCP tool map](#mcp-tool-map)

## Read one page

```bash
curl -sS -X POST "$FC/scrape" -H "$AUTH" -H "$JSON" \
  -d '{"url":"https://docs.example.com/guide","formats":["markdown"],"onlyMainContent":true}' > page.json
jq -r '.data.metadata | {statusCode, creditsUsed, cacheState}' page.json
jq -r '.data.markdown' page.json | head -c 20000
```

1 credit. Check `statusCode` before retrying: a 403 or 404 already cost 1 credit and will cost 1 again.

## Find pages, then read the best ones

```bash
curl -sS -X POST "$FC/search" -H "$AUTH" -H "$JSON" \
  -d '{"query":"rate limit headers site:docs.example.com","limit":5}' > hits.json
jq -r '.data.web[] | [.url, .title, (.description // "" | .[0:200])] | @tsv' hits.json
```

2 credits for up to 10 results. Pick the 1–3 URLs that answer the question and scrape those (1 each). Adding `scrapeOptions` instead would scrape all results at full price. For code, library, and error questions, `POST /search/developer` (MCP `firecrawl_developer_search`) costs the same and ranks docs and issues better. For papers, the Research Index tools are free.

## Pull a section of a site

```bash
curl -sS -X POST "$FC/map" -H "$AUTH" -H "$JSON" \
  -d '{"url":"https://docs.example.com","search":"authentication","limit":500}' > map.json
jq -r '.links[] | if type=="object" then .url else . end' map.json | grep '/auth' | head -50 > urls.txt
jq -Rn '{urls: [inputs], formats: ["markdown"]}' urls.txt > batch.json
python3 <skill-dir>/scripts/firecrawl_guard.py estimate batch-scrape batch.json --budget 60
curl -sS -X POST "$FC/batch/scrape" -H "$AUTH" -H "$JSON" -d @batch.json > job.json
curl -sS "$FC/batch/scrape/$(jq -r .id job.json)" -H "$AUTH" > status.json   # free; repeat until completed
```

1 credit for the map plus 1 per chosen URL, and you decide the list before spending. Large results paginate through `next`.

## Crawl when links must be followed

```json
{
  "url": "https://docs.example.com/guides/",
  "limit": 50,
  "ignoreQueryParameters": true,
  "includePaths": ["^/guides/.*"],
  "excludePaths": ["^/guides/archive/.*"],
  "maxDiscoveryDepth": 2,
  "scrapeOptions": {"formats": ["markdown"], "parsers": [{"type": "pdf", "maxPages": 5}]}
}
```

Every field matters:

- `limit` is the only real cap. Cancelling arrives too late on fast sites.
- `ignoreQueryParameters: true` stops query-string variants from Firecrawl's URL index being billed as separate pages. `sitemap: "skip"` also does this but loses sitemap discovery.
- Leave `crawlEntireDomain`, `allowSubdomains`, and `allowExternalLinks` off unless the user asked for them. Avoid `prompt`, which lets Firecrawl choose scope.
- Poll `GET /crawl/{id}` (free), and use `GET /crawl/{id}/errors` to see failures without re-crawling.

The MCP `firecrawl_crawl` tool blocks until the crawl finishes, so the limit you pass is the whole bill. It takes `scrapeOptions.pdfOptions.maxPages` rather than the REST `parsers` object.

## Structured fields

Reading markdown yourself costs 1 credit a page. The `json` format costs 5 and is worth it only when you need schema-shaped output over many pages and parsing them yourself would cost more context than credits. Put every field in one `json` format; a second LLM format adds another 4.

```json
{"url": "https://shop.example.com/item/42", "formats": [{"type": "json", "schema": {"type": "object", "properties": {"title": {"type": "string"}, "price": {"type": "string"}}, "required": ["title", "price"]}}]}
```

## PDFs

```json
{"url": "https://arxiv.org/pdf/1706.03762", "formats": ["markdown"], "parsers": [{"type": "pdf", "maxPages": 3}]}
```

1 credit per parsed page. Read the first pages, then raise `maxPages` only if needed. `parsers: []` costs 1 but returns base64 in `markdown`; decode it to a file and parse it locally if a local tool exists.

## Interactive pages

Prefer Playwright `code` (2 credits a minute) to a natural-language `prompt` (7). Set `ttl` and `activityTtl` low and delete the session when done:

```bash
curl -sS -X DELETE "$FC/scrape/$SCRAPE_ID/interact" -H "$AUTH"   # MCP: firecrawl_interact_stop
```

An abandoned prompt session can bill up to 70 credits at the default 10-minute TTL.

## Monitors

Create with the slowest cadence that still answers the question, read `estimatedCreditsPerMonth` in the response, and pause or delete monitors when their goal has passed (`PATCH`/`DELETE /monitor/{id}`). `POST /monitor/{id}/run` queues a paid check.

## MCP tool map

| Use | Avoid |
| --- | --- |
| `firecrawl_scrape`, `firecrawl_search`, `firecrawl_map`, `firecrawl_developer_search`, `firecrawl_research_search_papers` / `_read_paper` / `_related_papers`, `firecrawl_parse` (with page cap), `firecrawl_check_crawl_status`, `firecrawl_monitor_list` / `_get` / `_checks`, `firecrawl_search_feedback` and `firecrawl_feedback` (genuine feedback only) | `firecrawl_agent`, `firecrawl_agent_status` (banned); `firecrawl_crawl` without `limit` and `ignoreQueryParameters`; `firecrawl_interact` without `firecrawl_interact_stop`; `firecrawl_monitor_create` / `_run` without the user's go-ahead |

The MCP has no credit-usage or batch tool; use `scripts/firecrawl_guard.py balance` and REST batch scrape.
