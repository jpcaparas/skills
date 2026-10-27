# Exa Pricing (2026-10-27)

Sources: [pricing](https://exa.ai/docs/admin/pricing), [billing and rate limits](https://exa.ai/docs/admin/billing), [search quickstart](https://exa.ai/docs/search/quickstart), [Agent quickstart](https://exa.ai/docs/agent/quickstart), [Exa Connect](https://exa.ai/docs/agent/connect/overview), [monitors](https://exa.ai/docs/monitors/quickstart), [batch](https://exa.ai/docs/batch/quickstart), [x402](https://exa.ai/docs/integrations/payments/x402/quickstart), [error codes](https://exa.ai/docs/admin/error-codes), and the OpenAPI spec (`https://exa.ai/docs/exa-spec.yaml`). "Live" marks a figure confirmed by the `costDollars` of a real request on 2026-10-27; everything else is documentation.

## Table of Contents

- [Products and prices](#products-and-prices)
- [Agent](#agent)
- [Defaults that cost more](#defaults-that-cost-more)
- [What is and is not billed](#what-is-and-is-not-billed)
- [Limits](#limits)
- [Rate limits](#rate-limits)
- [Free tier and plans](#free-tier-and-plans)
- [Where the docs disagree](#where-the-docs-disagree)

## Products and prices

Base URL `https://api.exa.ai`, header `x-api-key: $EXA_API_KEY` (or `Authorization: Bearer`). Every base price covers up to 10 results.

| Product | Method + path | Price (USD) | Live check |
| --- | --- | --- | --- |
| Search `lite` | `POST /search` `type: "lite"` | $4 / 1K requests | $0.004 |
| Search `instant` (legacy) | `type: "instant"` | $4 / 1K | $0.004 |
| Search `auto` (default) | `type: "auto"` or unset | $7 / 1K | $0.007 |
| Search `fast` (legacy) | `type: "fast"` | $7 / 1K, "runs the same search" as `lite` | $0.007 |
| Deep Search | `type: "deep-lite"` or `"deep"` | $12 / 1K | $0.012 each |
| Deep Search (legacy) | `type: "deep-reasoning"` | $15 / 1K | $0.015 |
| Extra results | `numResults` above 10, any type | $1 / 1K results | 11 → $0.005, 20 → $0.014, 100 → $0.094 (lite); 25 → $0.022, 50 → $0.047 (auto) |
| AI page summaries | `contents.summary` on `/search` | $1 / 1K pages | 5 → +$0.005, 15 → +$0.015 |
| Contents | `POST /contents` | $1 / 1K pages **per content type** (`text`, `highlights`, `summary`) | 1, 2, 3 types on one page → $0.001, $0.002, $0.003 |
| Answer | `POST /answer` (also `/chat/completions` with `model: "exa"`) | $5 / 1K | $0.005 for `exa`, `exa-pro`, `exa-research`, `exa-fast` |
| Monitors | `POST /monitors` (per run) | $15 / 1K runs; +$1 / 1K results above 10; +$1 / 1K summaries | not measurable: run objects carry no cost |
| Agent | `POST /agent/runs` | see [Agent](#agent) | |
| Batch | `POST /batches` (Enterprise beta, header `Exa-Beta: batches-2026-06-06`) | no documented price or discount; items bill at their endpoint's rate (inferred) | 403 `FEATURE_DISABLED` on pay-as-you-go |
| Websets | `https://api.exa.ai/websets/v0/...` | separate Websets plan credits; per-credit prices only behind login | not tested |
| x402 / MPP keyless | `/search`, `/contents` paid in USDC | same per-type prices, priced upfront; `numResults` clamped to 10 | not tested |
| Hosted MCP | `https://mcp.exa.ai/mcp` | keyless: free and rate-limited (changelog: 3 QPS, 150 calls/day); with a key or OAuth: API rates (inferred) | keyless calls returned no cost |
| Team Management | `https://admin-api.exa.ai/team-management` | free; needs a service key | 401 with a normal API key |

## Agent

| `effort` | Price | Live |
| --- | --- | --- |
| `minimal` | $0.012 / run | $0.012 (3 searches) |
| `low` | $0.025 / run | $0.025 (3 searches) |
| `medium` | $0.10 / run | |
| `high` | $0.50 / run | |
| `xhigh` | $1.00 / run | |
| `auto` (**default**) | metered, default cap $5 | trivial question $0.022–$0.025; 26-row list $0.67–$0.68 |
| `ultra` | metered, default cap $20 | |

- Metered rates: $0.10 per Agent Compute Unit, $0.005 per search tool call, $0.02 per email, $0.07 per phone number. Live search charges varied ($0.003 for one search, $0.006 for one, $0.183 for 37), so read `costDollars` rather than recomputing.
- `budget.maxCostDollars` accepts $1–$100, applies only to `auto` and `ultra`, and on a fixed effort returns 400 "maxCostDollars is currently supported only for metered efforts" (live). A run that exceeds the cap "is billed the budget". `budget.maxDurationSeconds` (300–10,800) applies only to `ultra`.
- Fixed prices exclude contact enrichment ("billed per contact found, on top of the run's other costs") and Exa Connect provider calls.
- Exa Connect (`dataSources`, at most 5): Fiber.ai $0.02/credit; Similarweb $0.30/credit (1–15 credits a call); Baselayer $0.10–$4.00 an order; Affiliate.com and Particle $0.015/call; Financial Datasets $0.01/call; Jinko $0.005/call; Polymarket and Macrobond free. The spec scales "each quantity except `dataSources`" to the cap, so Connect charges may land on top of it.
- `/responses` (OpenAI-compatible, `model: "exa-agent"`, `reasoning.effort`) has no `budget` field.
- The hosted MCP `agent_run` tool defaults to `low`, unlike the API's `auto` (MCP source).

## Defaults that cost more

| Field | Default | Cheaper explicit choice | Saving |
| --- | --- | --- | --- |
| `/search` `type` | `auto` ($0.007) | `lite` ($0.004) | 43% |
| `/search` `type: "fast"` | legacy | `lite`, same search | 43% |
| `/search` `type: "deep-reasoning"` | legacy | `deep` | 20% |
| Agent `effort` | `auto`, $5 cap | `minimal`/`low`, or `auto` + `maxCostDollars: 1` | up to 99% |
| Agent `budget` on `ultra` | $20 cap | an agreed `maxCostDollars` | |
| `/contents` with no option | full `text` (45 KB a page live) | `highlights` or `text.maxCharacters` | context |
| `/search` `contents.text: true` | whole page (172 KB for 5 results live) | `highlights` (~2 KB a result) | context |
| `/answer` `text` | false | keep it false (true returned 278 KB live) | context |
| Monitor `trigger` | none = manual-only | keep manual while testing; `1d` in production | |

## What is and is not billed

Measured live:

- Highlights, bounded or unbounded `text`, and both together on `/search`: no extra charge.
- `outputSchema` on `auto` (text or object): no extra charge; answer in `output.content`, citations in `output.grounding`.
- `additionalQueries` on `deep`, `extras` (`links`, `imageLinks`), `maxAgeHours: 0`, and `livecrawl: "always"`: no extra charge; live fetching added ~9 s.
- Deep search bills results actually returned: `numResults: 30` returned 14 and billed $0.016; `numResults: 20` returned 7 and billed $0.012.
- `/contents` URLs that fail (404 `CRAWL_NOT_FOUND`, DNS failure, `UNSUPPORTED_URL`) are not billed, and a malformed URL does not reject the rest of the request.
- 400 validation errors are not billed. `503 SERVICE_OVERLOADED` "is not processed and is not billed" (docs).
- A cancelled Agent run reported $0 and zero usage after 12 s (docs say usage accrued before cancellation is billed).
- Polling `GET /agent/runs/{id}`, monitor runs, and lists carry no charge and do not count against QPS.

Not measured: subpages (every attempt returned none), monitor run charges, Websets, x402.

## Limits

| Parameter | Limit |
| --- | --- |
| `numResults` | 1–100, default 10 ("Contact sales for higher"); no pagination |
| `/contents` `urls` or `ids` | 1–100 a request |
| `text.maxCharacters`, `highlights.maxCharacters` | 1–1,000,000 |
| `additionalQueries` | 1–10, deep types only |
| `includeDomains` / `excludeDomains` | ≤1,200 each |
| `outputSchema` | ≤10 properties in total, ≤2 nesting levels |
| `maxAgeHours` | −1 to 720; not with `livecrawl` |
| Monitor `trigger.period` | minimum `1h`; single unit (`6h`, `1d`, `7d`) |
| Agent `dataSources` | ≤5 |

`lite` accepts only `query`, `objective`, `userIdentifier`, `metadata`, `category`, `numResults`, `contents.highlights`, `contents.text`, `contents.snapshotAsOf`, `userLocation`, domain and published-date filters, `moderation`, and `compliance`. Anything else returns `400 INVALID_REQUEST_BODY` naming the parameter (live for `contents.summary` and `contents.maxAgeHours: -1`).

## Rate limits

Team-wide, across keys: `/search`, `/answer`, `/chat/completions` 10 QPS; deep types 5 QPS; `/contents` 100 QPS; `/agent/runs` and `/responses` 5 QPS and 50 active runs (each run start counts as two requests); `/websets/*` 20 QPS. Buying $1,000 of credits within 30 days raises pay-as-you-go to 25 QPS for 90 days. On 429, honour `Retry-After` or back off exponentially.

## Free tier and plans

- Free: $10 of credits, available at signup and reset to $10 on the first of every month (no carry-over, first team only), plus a one-time $10 onboarding bonus. No card required. $10 is about 2,500 `lite` searches.
- Pay-as-you-go: prepaid credits, no subscription or minimum. Out of credits returns `402 NO_MORE_CREDITS`.
- Enterprise: volume discounts, postpaid invoicing, ZDR, custom QPS, more than 100 results, Batch API.

## Where the docs disagree

| Topic | One source | The other | Live |
| --- | --- | --- | --- |
| text + highlights on `/search` | quickstart: "both at no extra cost" | best practices: "each view is billed separately" | no extra cost |
| Exa's own `skill.md` prices | `auto` "$0.01–0.02", `deep` "$0.10–0.50" | pricing page: $0.007, $0.012 | pricing page is right |
| `/contents` summary | pricing table: per type **and** an AI summary column | x402: one content type | $0.001, not $0.002 |
| Result ceiling | spec: 100 | Enterprise copy: "requests above 25 results" | 50 and 100 worked on pay-as-you-go |
| Agent cancel billing | docs: usage before cancel is billed | — | reported $0 after 12 s |
| Agent search tool price | pricing: $0.005 a search | — | $0.003–$0.006 a search |
