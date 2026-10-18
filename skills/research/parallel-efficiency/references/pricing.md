# Parallel Pricing (2026-10-18)

Sources: [pricing](https://docs.parallel.ai/getting-started/pricing), [parallel.ai/pricing](https://parallel.ai/pricing), [rate limits](https://docs.parallel.ai/getting-started/rate-limits), [search modes](https://docs.parallel.ai/search/modes), [choose a processor](https://docs.parallel.ai/task-api/guides/choose-a-processor), [FindAll pricing](https://docs.parallel.ai/findall-api/core-concepts/findall-generator-pricing), [Monitor quickstart](https://docs.parallel.ai/monitor-api/monitor-quickstart), [FAQs](https://docs.parallel.ai/resources/faqs), [warnings and errors](https://docs.parallel.ai/resources/warnings-and-errors), and the public OpenAPI spec. All figures are documentation; none was billed live for this skill.

## Table of Contents

- [Products and prices](#products-and-prices)
- [Defaults that cost more](#defaults-that-cost-more)
- [What is and is not billed](#what-is-and-is-not-billed)
- [Rate limits](#rate-limits)
- [Free tiers and credits](#free-tiers-and-credits)
- [Where the docs disagree](#where-the-docs-disagree)

## Products and prices

Base URL `https://api.parallel.ai`, header `x-api-key: $PARALLEL_API_KEY`.

| Product | Method + path | Price (USD) | Notes |
| --- | --- | --- | --- |
| Search | `POST /v1/search` | `turbo`/`fast` $1 per 1K requests; `basic`/`advanced` $5 per 1K; 10 results included; +$1 per 1K extra results | `max_results` max 20, so one call costs at most $0.011 (fast) or $0.015 (advanced) |
| Image Search | `POST /v1/images/search` | `fast` $1 per 1K; `advanced` $5 per 1K | Up to 20 results at no extra cost |
| Extract | `POST /v1/extract` | $1 per 1K URLs | Up to 20 URLs a request |
| Task | `POST /v1/tasks/runs` | per 1K successful runs: lite 5, base 10, core 25, core2x 50, pro 100, ultra 300, ultra2x 600, ultra4x 1,200, ultra8x 2,400 | "Failed runs are not billed"; one charge per run regardless of field count |
| Task Group | `POST /v1/tasks/groups`, `POST /v1/tasks/groups/{id}/runs` (≤1,000 inputs a POST) | Task price per run | Group creation itself is not priced |
| Responses | `POST /v1/responses` (`model: "parallel"`) | per 1K successful requests: low 10, medium 50 (default), high 250 | "bills per request, not per token" |
| FindAll | `POST /v1beta/findall/runs` | preview $0.10 + $0; base $0.25 + $0.03/match; core $2 + $0.15/match; pro $10 + $1/match | `match_limit` 5–1,000 (preview 5–10 candidates) |
| FindAll extend | `POST /v1beta/findall/runs/{id}/extend` | no fixed fee; new matches at the run's rate | only after `match_limit_met`; not for preview |
| FindAll enrich | `POST /v1beta/findall/runs/{id}/enrich` | Task processor price × matches | `processor` defaults to `core` |
| FindAll cancel | `POST /v1beta/findall/runs/{id}/cancel` | none | "does not reverse charges for work that already completed" |
| Entity Search | `POST /v1beta/findall/entity-search` | $5 per 1K requests, 100 results included; +$0.05 per 1K extra results | `match_limit` 5–1,000, default 100 |
| Monitor | `POST /v1/monitors` | `lite` $3 per 1K executions (default); `base` $10 per 1K | `frequency` 1h–30d; runs once at creation |
| Monitor trigger | `POST /v1/monitors/{id}/trigger` | one execution (inferred) | |
| Chat (beta) | `POST /v1beta/chat/completions` | not on the current pricing page | legacy |
| Search MCP | `https://search.parallel.ai/mcp` | free anonymously (forced to `fast`); with an API key, presumably Search rates | |
| Task MCP | `https://task-mcp.parallel.ai/mcp` | Task prices; processor for `createDeepResearch` undocumented | needs an API key |
| Agentic payments | `https://parallelmpp.dev/api/{search,extract,task}` | Extract $0.01 per URL (10× API); task $0.10 pro, $0.30 ultra | "Polling is free" |
| Account | `GET /service/v1/balance`; **`POST /service/v1/balance/add` charges the card** | — | OAuth account token |

Processor guidance from the docs: "Use `lite` or `base` for simple enrichments, `core` for reliable accuracy on up to 10 output fields, and `pro` or `ultra` when reasoning depth is critical." Approximate field capacity: lite ~2, base ~5, core/core2x ~10, pro/ultra ~20, ultra2x+ ~25. Latency: lite 10–60 s, base 15–100 s, core 1–5 min, pro 2–10 min, ultra 5–25 min, ultra8x up to 2 h.

Search mode guidance: "Start with `fast`. It delivers high-quality results in around 700ms and is the right choice for most agents." `turbo` (~200 ms) supports English and Japanese only and no path prefixes; `basic` gives extended snippets (~1 s); `advanced` is multi-hop.

## Defaults that cost more

| Field | Default | Cheaper explicit choice | Saving |
| --- | --- | --- | --- |
| Search / Image Search `mode` | `advanced` ($5/1K) | `fast` ($1/1K) | 80% |
| Responses `reasoning.effort` | `medium` ($50/1K) | `low` ($10/1K) | 80% |
| FindAll enrich `processor` | `core` ($25/1K matches) | `lite`/`base` ($5–10/1K) | 60–80% |
| CLI research processor | `pro` | `core` or `base` | 75–90% |
| CLI FindAll generator | `core` | `preview`, then `base` | |
| CLI search mode | `basic` ($5/1K) | `fast` | 80% |
| Pro/ultra `task_spec` | auto schema (deep research) | explicit `output_schema` | fewer re-runs |

## What is and is not billed

- Task and Responses bill only successful runs.
- Monitors bill every execution, "even if it finds no events".
- FindAll charges the fixed fee per run and the per-match fee per match; cancellation keeps charges for completed work; adding an enrichment to a finished run requeues it.
- Status, result, events (SSE), and polling `GET` calls carry no documented price and do not count toward rate limits.
- Task Groups check the balance for the whole batch up front; pro and ultra reserve more credit, so a 402 can occur with a positive balance.
- Pay-per-use data connectors bill per successful connector call, separately from the processor.

## Rate limits

Default limits (rolling 60-second window, POSTs only): Search 600/min, Image Search 600/min, Extract 600/min, Tasks and Task Groups 2,000/min, Chat 300/min, FindAll 300/hour, Entity Search 600/min, Monitor 300/min. A 429 means slow down; retrying faster is not cheaper.

## Free tiers and credits

- $5 of free credit per organisation per month with a card on file; unused balance expires at month end. Parallel says it covers about 5,000 Searches, 5,000 Extracts, 1,000 Task runs, or 1,666 Monitor executions. Marketplace and postpaid organisations are not eligible.
- Signup offers "up to $80"; qualified startups "up to $250".
- Search MCP anonymous use is free with "generous rate limits for hobby use"; `session_id` is used for free-tier rate limiting.
- Free data connectors: `pubmed`, `clinical_trials`, `chembl`, `biorxiv`, `npi_registry`, `cms_coverage`.

## Where the docs disagree

| Topic | One source | The other |
| --- | --- | --- |
| FindAll rate limit | rate-limits page: 300/hour | parallel.ai/pricing: 25/hour |
| Task rate limit scope | rate-limits page: POSTs only | Task lifecycle page: "all POST and GET requests" |
| Task cancel | glossary: run ID lets you "cancel the run" | OpenAPI spec: no cancel endpoint |
| Monitor `core` processor | API enum includes it | pricing page lists only lite and base |
| `-fast` processors | 2025-12 changelog: same price as standard | current processor list omits them |
