# Firecrawl Pricing (2026-10-18)

Sources: [billing](https://docs.firecrawl.dev/billing), [pricing](https://www.firecrawl.dev/pricing) ("Effective September 4, 2026"), [rate limits](https://docs.firecrawl.dev/rate-limits), the [v2 OpenAPI spec](https://docs.firecrawl.dev/api-reference/v2-openapi.json), and the feature pages linked below. **Live** marks a figure Firecrawl actually billed in this skill's spike (`references/evidence.md`); everything else is documentation only.

## Table of Contents

- [Endpoints](#endpoints)
- [Per-page modifiers](#per-page-modifiers)
- [When a request is billed](#when-a-request-is-billed)
- [Plans and top-ups](#plans-and-top-ups)
- [Rate limits and concurrency](#rate-limits-and-concurrency)
- [Where the docs disagree](#where-the-docs-disagree)

## Endpoints

Base URL `https://api.firecrawl.dev/v2`, header `Authorization: Bearer $FIRECRAWL_API_KEY`.

| Endpoint | Path | Credits | Notes |
| --- | --- | --- | --- |
| Scrape | `POST /scrape` | 1 per page (**live**) | Plus modifiers below |
| Batch scrape | `POST /batch/scrape`, `GET/DELETE /batch/scrape/{id}`, `GET …/errors` | 1 per URL | Status polling free (documented) |
| Crawl | `POST /crawl`, `GET/DELETE /crawl/{id}`, `GET …/errors`, `GET /crawl/active` | 1 per page (**live**: limit 5 → 5, limit 40 → 40) | `limit` defaults to 10,000; billed as pages complete |
| Map | `POST /map` | 1 per call (**live**: 1,612 URLs → 1) | Any `limit` up to 100,000 |
| Search | `POST /search` | 2 per 10 results, rounded up (**live**: 3 → 2, 10 → 2, 11 → 4) | `limit` is per source; web+news at limit 5 returned 10 results for 2 (**live**) |
| Search + scrape | `POST /search` with `scrapeOptions` | search price + scrape price per result (**live**: 2 results → 4) | |
| ZDR search | `enterprise: ["zdr"]` | 10 per 10 results | Enterprise; `["anon"]` stays 2 per 10 |
| Developer search | `POST /search/developer` (MCP `firecrawl_developer_search`) | 2 per 10 results | |
| Research Index | `GET /search/research/papers…` (MCP `firecrawl_research_*`) | free | Pricing FAQ: "free across every category" |
| Gov results | `/search` with `categories: ["gov"]` | "add no search credits" | |
| Parse | `POST /parse` (multipart, 50 MB) | 1 per PDF page | DOCX/XLSX pricing not stated |
| Interact | `POST /scrape/{id}/interact`, `POST /interact`, `…/execute`, `DELETE` | 2 per browser minute with `code`, 7 with `prompt`; ZDR 4 / 9; 1-minute minimum | Session `ttl` default 600 s, `activityTtl` 300 s |
| Monitor | `POST/GET/PATCH/DELETE /monitor…`, `…/run`, `…/checks` | scrape target: 1 per URL per check; crawl target: 1 per discovered page per check; search target: 2 per 10 results per check; judge +1 per changed page | Response shows `estimatedCreditsPerMonth`; pricing page also mentions a "flat 7 credits per page per check" extraction engine |
| Change tracking | `changeTracking` format | git-diff: free (**live**: 1 total); `json` mode: 5 per page | Bypasses the cache |
| Search feedback | `POST /search/{id}/feedback` | refunds 1 (**live**), cap 100 per day | First submission per job |
| Account | `GET /team/credit-usage`, `/team/credit-usage/historical`, `/team/queue-status`, `/team/token-usage` | free (**live** for credit-usage and queue-status) | |
| **Agent (banned)** | `POST /agent` | dynamic; "most agent runs consume a few hundred credits"; `maxCredits` default 2,500; 5 free runs a day | Failed runs are not billed; cancellation is cooperative |
| **Extract (banned)** | `POST /extract` | token-based, 15 tokens = 1 credit | `includeSubdomains` defaults to `true`; shares the agent rate limit |
| **Deprecated v1** | `/v1/deep-research`, `/v1/llmstxt` | 1 per URL analysed / 1 + 1 per URL | Unmaintained since 2025-06-30 |
| X / Twitter URLs | via scrape | 30 per request (1 + 29 Grok); 34 with json | Excluded by this skill |
| LinkedIn URLs | via scrape | 5–40 per request by provider | Excluded; "Every request is charged" |

## Per-page modifiers

They apply to every page scraped by scrape, batch, crawl, and search-with-scrape, and they stack.

| Modifier | Extra credits |
| --- | --- |
| `json`, `question`/`query`, `highlights`, `audio`, `video` formats | +4 each (**live**: json → 5; markdown + summary + json → 5) |
| `summary`, `branding`, `screenshot` (incl. `fullPage`), `links`, `images`, `html`, `rawHtml` | 0 (**live**) |
| PDF parsing (default `parsers`) | +1 per PDF page (**live**: 15-page PDF → 15 total, `maxPages: 2` → 2) |
| `parsers: []` on a PDF | 1 flat (**live**), returns base64 |
| `zeroDataRetention` | +1 |
| `redactPII` | +4, and +4 per extra PDF page |
| `checkPromptInjection` | +4; 5 billed if the scrape then fails |
| `lockdown` | +4 on cache hit; 1 on miss with no document |
| `proxy: "enhanced"` / `auto` escalation | 0 since 2026-08-17 |
| `maxAge` cache hit | 0 saving: still 1 (**live**) |

## When a request is billed

- "What decides the charge is whether Firecrawl returned a document." A 403/404/500 page is a document: 1 credit (**live**: 404 → 1, 500 → 1).
- No document, no charge: DNS failure → 0, 408 timeout → 0 (**live**).
- Exceptions that bill without a document: threat-protection scans (2 per URL), the prompt-injection guard (5), lockdown misses (1), monitor checks that error (1 per page), and interact sessions (per minute).
- Crawl and batch credits post asynchronously as pages finish; they can keep appearing "minutes or hours after submission".
- A cancelled crawl keeps every page it already scraped (**live**: cancelled after 4 s, all 40 pages billed).

## Plans and top-ups

| Plan | Monthly credits | Price (annual / monthly billing) | Concurrent browsers | Pay-as-you-go: credits per $5 | Overage allowance |
| --- | --- | --- | --- | --- | --- |
| Free | 1,000 | $0 | 2 | not available (402 at zero) | — |
| Hobby | 5,000 | $16 / $19 | 5 | 1,000 | 1,500 |
| Standard | 100,000 | $83 | 25 | 2,000 | 30,000 |
| Growth | 500,000 | $333 | 50 | 2,500 | 150,000 |
| Scale | 1,000,000 | $599 | 100 | 5,000 | 600,000 |

Plan credits do not roll over except on annual Scale (1 month) and annual Enterprise (2 months). Bought credits persist until the subscription is cancelled. Upgrades charge the full new price immediately with no proration.

## Rate limits and concurrency

Requests per minute, Free / Hobby / Standard / Growth / Scale:

- `/scrape`, `/map`, `/search`: 10 / 100 / 500 / 5,000 / 10,000
- `/crawl`, `/agent`: 2 / 20 / 100 / 1,000 / 2,000
- `/interact`: 2 / 20 / 100 / 1,000 / 1,500

Queued jobs time out after 48 hours. The tested Standard account reported `maxConcurrency: 50` from `/team/queue-status`. Scrape, Search, Parse, and Interact also work keyless, capped per IP per day (numbers unpublished).

## Where the docs disagree

| Topic | One source | The other | Live result |
| --- | --- | --- | --- |
| Map | billing and map docs: 1 per call | pricing page: "1 / page" | 1 per call |
| Cache hits | scrape docs: "still cost 1 credit" | marketing page: "Cached pages are free" | 1 credit |
| Crawl preflight | crawl docs: 402 if credits cannot cover `limit` | billing: limit is not reduced if allowed "including through overage"; omitted limit checks only 1 credit | A `limit: 50000` crawl was accepted on a balance of about 3,000 credits |
| Batch rate limit | billing: shares the scrape limit | rate-limits page: shares the crawl limit | not tested |
| Browser concurrency | rate-limits page: by plan | browser page: 20 on all plans | not tested |
