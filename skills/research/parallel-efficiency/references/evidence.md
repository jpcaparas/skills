# Evidence

A **2026-10-18 UTC snapshot**. It is evidence from that day, not a contract.

## What was checked, and how

- **Documentation**: `llms.txt`, `llms-full.txt`, more than 45 `.md` doc pages, the public OpenAPI spec (`https://docs.parallel.ai/public-openapi.json`), the account service spec, and parallel.ai/pricing. The pricing page was re-read in full on 2026-10-18 to confirm every figure in `references/pricing.md`.
- **Request shapes**: every REST body in `references/recipes.md` was checked against the OpenAPI schemas (`V1SearchRequest`, `V1ExtractRequest`, `TaskRunInput`, `TaskGroupRunRequest`, `FindAllRunInput`, `FindAllExtendInput`, `CreateMonitorRequest`, `MonitorEventStreamSettings`, `ResponseCreateRequest`).
- **CLI defaults**: read from the CLI reference page, not executed.
- **Live calls**: the Parallel Search MCP, through an MCP client:
  - `web_search` with an objective and two queries returned 10 results, each with 1.9–3.0k characters of excerpts, 56 KB in total, with `search_id`, `session_id`, `warnings`, and `metadata` fields.
  - `web_fetch` of one docs page returned 5.3 KB as excerpts against 15.6 KB with `full_content: true`.
  - An unauthenticated MCP `initialize` handshake succeeded against `search.parallel.ai/mcp`; `task-mcp.parallel.ai/mcp` returned "Authentication required".

## Not measured

No `PARALLEL_API_KEY` was available, so no REST call was billed and none of the prices was confirmed by an invoice or `usage` array. Specifically untested:

- whether live fetch (`fetch_policy`), `location`, or domain filters change Search price;
- whether Extract URLs that land in `errors[]` are billed;
- whether `-fast` processors are still accepted;
- the Chat API's current price;
- Monitor `core` pricing and whether `trigger` and backfill are billed;
- which rate limits are enforced for FindAll, Responses, and Monitor;
- the processor behind Task MCP `createDeepResearch`;
- Search MCP free-tier limits and whether authenticated MCP calls bill at Search rates.

## Reproduce cheaply (with a key)

```bash
curl -sS https://api.parallel.ai/v1/search -H "x-api-key: $PARALLEL_API_KEY" -H "Content-Type: application/json" \
  -d '{"objective":"Parallel search modes","search_queries":["parallel search modes"],"mode":"fast"}' | jq '.usage'
```

One `fast` search costs $0.001. Compare its `usage` with the same call without `mode` (default `advanced`, $0.005) to confirm the default.
