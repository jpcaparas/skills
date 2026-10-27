# Gotchas

Surprises that cost money, context, or time, with the fix. "Live" means seen in the 2026-10-27 spike.

## The default search type is the dearer one

`/search` without `type` runs `auto` at $0.007; `lite` is $0.004; for one factual query live, 7 of its 10 results and its top two matched `auto`. Legacy `fast` is documented as "the same search" as `lite` but bills $0.007. Send `type: "lite"` and move to `auto` only for a parameter `lite` rejects.

## `lite` is strict about parameters

Live: `contents.summary` and `contents.maxAgeHours: -1` on `lite` returned `400 INVALID_REQUEST_BODY`. Any non-null value counts as set, so `false`, `0`, and `[]` fail too. Build `lite` bodies from an allow-list, not by toggling fields off. The 400 is free, but it costs a round trip and often a retry at `auto`.

## `lite` can return fewer results

`lite` never live-fetches. When `text` or `highlights` is requested, results with no cached copy are dropped. If a `lite` search returns noticeably fewer results than `numResults`, retry once on `auto`, not in a loop.

## An uncapped Agent run can cost $5

`effort` defaults to metered `auto` with a $5 cap, and `ultra` to a $20 cap. Live, a one-line fact cost $0.022–0.025 on `auto`, while a list of New Zealand developer-tool startups ran 2.5 minutes, 37–40 searches, and $0.67–0.68. Send a fixed effort for known scope, or `auto` with `budget.maxCostDollars`. Sending `budget` with a fixed effort is a 400.

## Fixed Agent prices are not all-in

Emails ($0.02) and phone numbers ($0.07) are "billed per contact found, on top of the run's other costs", and Exa Connect providers bill per call: Similarweb at $0.30 a credit can reach $4.50 for one call, and Baselayer up to $4 an order. The spec scales everything except `dataSources` to the cap, so Connect charges may exceed it. Get approval before attaching providers or asking for contacts.

## Cancel throws work away

`POST /agent/runs/{id}/cancel` "terminates without returning any results". `/stop`, which returns partial results, returned 400 "Graceful stop is currently supported only for ultra effort runs" on an `auto` run live. Size the cap so you never need to cancel. Live, a run cancelled after 12 s reported $0 and zero usage, but the docs say usage accrued before cancellation is billed.

## Agent costs read zero until the run ends

While a run is `running`, `costDollars.total` is 0. Do not treat that as "cheap so far"; the figure is only final at `completed`, `failed`, or `cancelled`.

## `/contents` bills per view and defaults to full text

Each of `text`, `highlights`, and `summary` is billed per page: $0.003 for all three on one page live. A bare `{"urls": [...]}` returned the full 45 KB page. Pick one view.

## Some responses are much larger than they need to be

| Request | Live size |
| --- | --- |
| `/answer` with `text: true` | 278 KB for one question |
| `/search` `lite`, 5 results, `text: true` | 172 KB |
| `/contents` one page, no options | 45 KB |
| `/search` `lite`, 10 results, `highlights: true` | 25 KB |
| `/search` `lite`, 30 `people` results, no contents | 68 KB |

Price is unchanged, so cap `maxCharacters`, keep `numResults` to what you will read, and write responses to files.

## Monitors bill silently

A monitor bills $0.015 or more a run until deleted, and its run objects carry no cost field, so spend only shows up in the dashboard or the key usage API. Creating one requires a public HTTPS webhook (live: `example.com` was rejected as a private address; `httpbin.org` was accepted). A monitor without `trigger` did not run at creation live. Delete test monitors before ending the session.

## Exa's own agent skill has stale prices

`https://exa.ai/docs/skill.md` lists `auto` at "$0.01–0.02" and `deep` at "$0.10–0.50" a request; the pricing page and live billing say $0.007 and $0.012. It also calls content options "free to combine" and "billed separately" in different places. Trust the pricing page and `costDollars`.

## Batch is not a discount

The Batch API is Enterprise-only (live: 403 `FEATURE_DISABLED`) and documents no discount. Its sample agent items omit `effort`, so every such item runs `auto` with a $5 cap. Set `effort` on each item.

## Keyless payments clamp results

x402 and MPP silently clamp `numResults` to 10 and price requests before they run. Use an API key when more results are needed.

## Rate limits queue, then 429

Responses may carry `x-exa-queued` and `x-exa-queue-ms` when a request waited in the rate-limit queue. A 429 means slow down: honour `Retry-After`. Agent run starts count as two requests and are limited to 50 active runs (`429 CONCURRENCY_LIMIT_REACHED`).

## Docs disagree

The pricing page, best practices, the changelog, and the spec contradict each other on content billing, result ceilings, and summary pricing; see the table in `references/pricing.md`. When a figure matters, send one minimal request and read `costDollars`.
