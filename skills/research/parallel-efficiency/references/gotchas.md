# Gotchas

Surprises that cost money or time, with the fix.

## The defaults are the expensive tier

Search and Image Search default to `advanced` ($5/1K) even though the docs recommend starting with `fast` ($1/1K). Responses defaults to `medium` ($50/1K), FindAll enrichments to `core`, and the CLI to `pro` (research), `core` (enrich, FindAll), and `basic` (search). Send every one of these fields explicitly.

## Spend limits do not stop spending

"Limits are notify-only; they never block requests." A dashboard limit sends an email; the requests continue. The agent's own budget and the cost script are the only hard stop.

## Task runs cannot be cancelled

The OpenAPI spec has no cancel endpoint for Task runs, although the glossary mentions cancelling one; FindAll and Monitors do have cancel endpoints. A mistaken `ultra8x` group of 100 inputs is $240 that will be billed. Run one input, inspect it, then submit the group.

## Cancelling FindAll keeps the charges

"Cancellation does not reverse charges for work that already completed", and work in flight may finish anyway. Adding an enrichment to a finished run requeues it and bills again.

## FindAll `pro` and big `match_limit`s

At $1 per match, `pro` with `match_limit: 1000` can cost $1,010 before enrichments, and each enrichment adds processor price × matches. "For match counts above 50, the per-match cost becomes more significant than the fixed cost." Start with `preview`, then `base` at 10–20 matches, and extend.

## Monitors bill for nothing happening

Every check is billed "even if it finds no events", starting with one immediately at creation, and monitors run until cancelled. Snapshot monitors also pay for their Task run. Choose `1d` or slower and agree a cancel date.

## A 402 with money in the account

Task Groups check the balance for the whole batch up front, and `pro`/`ultra` reserve more than `base`/`lite`. A large group can return 402 on a positive balance. Split the group or top up; do not retry in a loop.

## v1beta bodies fail on v1

On `/v1/extract`, top-level `excerpts`, `full_content`, and `fetch_policy` return 422; they belong inside `advanced_settings`. Use `/v1/search` and `/v1/extract` for new work, and keep FindAll on its documented `/v1beta` paths.

## Excerpts are free to shrink

Price does not depend on excerpt length, so cutting `max_chars_total` saves context at no cost. The CLI sends `--excerpt-max-chars-total 60000` by default; the Search MCP returned about 56 KB for one 10-result call. `full_content` can be tens of thousands of tokens per page.

## Domain filters can backfire

`include_domains` narrows results and "can reduce result quality by excluding relevant pages", which tends to cause a second paid query. Prefer a precise objective and queries; filter only when the user requires a source.

## The CLI cannot run a FindAll preview

`parallel-cli findall run -g` accepts `base`, `core`, and `pro`; there is no `preview`. `--dry-run` only previews the schema through the ingest endpoint. Use the REST API for the $0.10 preview.

## Agentic payment endpoints cost more

Through MPP/x402, Extract is $0.01 per URL against $0.001 on the API. Use the API key route when one exists.

## Pricing pages disagree

FindAll's rate limit is 300/hour in the docs and 25/hour on parallel.ai/pricing; Monitor's `core` processor appears in the API enum but has no price; `-fast` processors appear in an old changelog only. See `references/pricing.md`. When a figure matters, check the current pricing page and the response's `usage` array.
