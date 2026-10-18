# Gotchas

Surprises that cost credits or time, with the fix. "Live" means seen in the 2026-10-18 spike.

## A small site can bill hundreds of pages

Live: `POST /crawl {"url": "https://example.com/", "limit": 50000}` billed 809 credits in about 10 seconds. `example.com` has one page; the crawl followed 808 query-string variants (`?rl=…`, `?fcbench=…`, `?quota=dead`) that other users had scraped and Firecrawl's URL index remembered. `map` on the same site returned 1 URL.

Fix: always send `ignoreQueryParameters: true` (or `sitemap: "skip"`) and a `limit` sized to the job. Either flag alone held the same crawl to 1 page.

## The limit is the only brake

Crawls run fast and bill as pages complete. A `DELETE` 4 seconds into a 40-page crawl arrived after it had finished; all 40 were billed. A crawl submitted without `limit` gets 10,000, and with pay-as-you-go on it keeps going past a zero balance into the overage allowance (30,000 credits on Standard).

## Error pages are billed, failures are not

A 403, 404, or 500 from the target is still a document: 1 credit each. DNS failures and 408 timeouts cost nothing. Retrying a blocked URL is paying again for the same 403; read `metadata.statusCode` first.

## Caching saves time, not credits

`maxAge` (default 2 days) serves cached copies at the same 1 credit (`cacheState: "hit"`). Do not raise `maxAge` hoping to save money, and do not set `maxAge: 0` unless freshness matters; it is slower and "more likely to fail".

## One bad URL rejects the whole batch

Live: a batch containing `"not a url"` returned HTTP 400 for the entire job, even though `ignoreInvalidURLs` defaults to true. Validate URLs before batching. The 400 itself was free.

## `parsers: []` floods context

It keeps a PDF at 1 credit, but the response's `markdown` field held the whole file as base64: 2.9 MB for a 15-page paper. Write it to disk, decode it, and parse locally; never print it.

## Search counts results across sources

`limit` applies per source. `limit: 5` with `sources: ["web", "news"]` returned 10 results (still 2 credits, because billing rounds per 10 results overall). `limit: 11` costs as much as 20.

## LLM formats are cheap to add by accident

Each of `json`, `question`/`query`, `highlights`, `audio`, and `video` adds 4 credits a page; on a 1,000-page crawl that is 4,000 extra credits. The MCP `firecrawl_scrape` tool exposes `query` and `json` formats next to `markdown`; check the format list you send.

## Monitors bill forever

A monitor runs until paused or deleted, whether or not the page changes. The account tested had a 30-minute monitor with the judge enabled, estimated at 2,880 credits a month, for an event page created two months earlier. List monitors when investigating a bill.

## The docs push you toward `/agent`

`/extract` pages say "Use /agent instead", and the choosing-an-extractor guide recommends agent when URLs are unknown. This skill does not follow that advice: search + scrape answers the same questions for single-digit credits.

## Credits post late

Crawl and batch credits can keep appearing "minutes or hours after submission". When measuring a job's cost, use its `creditsUsed`, not a balance delta, especially when something else (a monitor) shares the key.

## Pricing pages disagree

Firecrawl's pricing page, billing docs, and marketing pages contradict each other on map pricing, cache billing, and crawl preflight (see the table in `references/pricing.md`). When it matters, run one minimal request and read `creditsUsed`.
