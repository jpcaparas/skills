# Cheap Routes, Copy-Ready

Each recipe is the lowest-cost way to do one job. Price anything beyond Search and Extract first:

```bash
C="python3 <skill-dir>/scripts/parallel_cost.py"
$C estimate tasks/runs body.json --budget-usd 0.10   # exit 0 ok, 2 warn, 3 blocked
```

REST examples assume:

```bash
P=https://api.parallel.ai
AUTH="x-api-key: $PARALLEL_API_KEY"
JSON="Content-Type: application/json"
```

Write responses to files and read them with `jq`. Check each response's `usage` array (for example `sku_search`, `sku_extract_excerpts`) to see what was billed.

## Table of Contents

- [Search](#search)
- [Extract the chosen pages](#extract-the-chosen-pages)
- [Responses for a quick grounded answer](#responses-for-a-quick-grounded-answer)
- [Task runs](#task-runs)
- [Task Groups](#task-groups)
- [Entity Search and FindAll](#entity-search-and-findall)
- [Monitors](#monitors)
- [CLI flags that override expensive defaults](#cli-flags-that-override-expensive-defaults)
- [MCP](#mcp)

## Search

```bash
curl -sS "$P/v1/search" -H "$AUTH" -H "$JSON" -d '{
  "objective": "Find the official changelog entry for Postgres 18 logical replication changes",
  "search_queries": ["postgres 18 release notes", "postgres 18 logical replication"],
  "mode": "fast",
  "max_chars_total": 12000,
  "session_id": "task-postgres18"
}' > search.json
jq -r '.results[] | [.url, .title] | @tsv' search.json
```

$0.001. Put 2–5 short queries in one request (they do not multiply cost) and describe the goal in `objective`. Raise `mode` to `advanced` only when `fast` results are clearly insufficient. Avoid `include_domains` unless required; the docs warn it can cut relevant pages and force a re-query.

## Extract the chosen pages

```bash
curl -sS "$P/v1/extract" -H "$AUTH" -H "$JSON" -d '{
  "urls": ["https://www.postgresql.org/docs/18/release-18.html"],
  "objective": "What changed in logical replication?",
  "max_chars_total": 8000
}' > extract.json
jq -r '.results[0].excerpts[]' extract.json; jq '.errors' extract.json
```

$0.001 a URL, up to 20 URLs. Keep `advanced_settings.full_content` off unless the whole page is the deliverable. On `/v1/extract`, `full_content`, `fetch_policy`, and `excerpt_settings` belong inside `advanced_settings`; top-level versions return 422.

## Responses for a quick grounded answer

```bash
curl -sS "$P/v1/responses" -H "$AUTH" -H "$JSON" -d '{
  "model": "parallel",
  "input": "Which Postgres version introduced the pg_stat_io view?",
  "reasoning": {"effort": "low"}
}' > answer.json
```

$0.01 at `low`. The default `medium` is $0.05 and `high` $0.25. Each follow-up with `previous_response_id` is billed again; open with the effort the question needs and follow up at `low`.

## Task runs

```bash
curl -sS "$P/v1/tasks/runs" -H "$AUTH" -H "$JSON" -d '{
  "processor": "base",
  "input": {"company": "Stripe", "website": "stripe.com"},
  "task_spec": {"output_schema": {"type": "json", "json_schema": {"type": "object", "properties": {
    "founding_year": {"type": "string"}, "headquarters": {"type": "string"}, "ceo": {"type": "string"}}}}}
}' > run.json
curl -sS "$P/v1/tasks/runs/$(jq -r .run_id run.json)/result" -H "$AUTH" > result.json   # blocks; free
```

Pick the processor by field count and difficulty: `lite` ~2 fields, `base` ~5, `core` ~10, `pro` ~20 or exploratory research, `ultra*` only for hard deep research the user asked for. A run costs the same for 1 field or 20, so ask for everything in one run. Give `pro`/`ultra` an explicit `output_schema` unless an auto-structured report is the goal. Runs cannot be cancelled once submitted.

## Task Groups

Run one input on its own and check the output before submitting the group:

```bash
curl -sS -X POST "$P/v1/tasks/groups" -H "$AUTH" -H "$JSON" -d '{}' > group.json
G=$(jq -r .taskgroup_id group.json)
python3 <skill-dir>/scripts/parallel_cost.py estimate "tasks/groups/$G/runs" inputs.json --budget-usd 5
curl -sS -X POST "$P/v1/tasks/groups/$G/runs" -H "$AUTH" -H "$JSON" -d @inputs.json
curl -sS "$P/v1/tasks/groups/$G" -H "$AUTH"   # status, free
```

`inputs.json` holds `{"default_task_spec": {...}, "inputs": [{"processor": "base", "input": ...}, ...]}` with at most 1,000 inputs per POST. The whole batch's cost is reserved up front.

## Entity Search and FindAll

When you just need candidate people or companies, Entity Search ($0.005 for 100) is enough:

```bash
curl -sS "$P/v1beta/findall/entity-search" -H "$AUTH" -H "$JSON" -d '{
  "entity_type": "companies", "objective": "Developer-tools startups in Auckland", "match_limit": 25
}'
```

For a verified list, test the query with `preview` ($0.10), then run `base` with a small `match_limit` and extend:

```bash
curl -sS "$P/v1beta/findall/runs" -H "$AUTH" -H "$JSON" -d '{
  "objective": "...", "entity_type": "companies", "match_conditions": [...],
  "generator": "preview", "match_limit": 10
}'
# then generator "base", match_limit 20; if it meets the limit and you need more:
curl -sS -X POST "$P/v1beta/findall/runs/$RUN/extend" -H "$AUTH" -H "$JSON" -d '{"additional_match_limit": 20}'
```

Price enrichments with `--matches`: `parallel_cost.py estimate findall/runs/$RUN/enrich enrich.json --matches 40`, and set `"processor": "lite"` or `"base"` for simple fields. Pass previous matches as `exclude_list` when refreshing a list.

## Monitors

```bash
python3 <skill-dir>/scripts/parallel_cost.py estimate monitors monitor.json   # prints monthly_usd
curl -sS "$P/v1/monitors" -H "$AUTH" -H "$JSON" -d '{
  "type": "event_stream", "frequency": "1d", "processor": "lite",
  "settings": {"query": "Postgres 19 beta release announced"}
}'
curl -sS -X POST "$P/v1/monitors/$MON/cancel" -H "$AUTH"   # irreversible; stops billing
```

Tell the user the monthly figure and when the monitor should be cancelled before creating it.

## CLI flags that override expensive defaults

| Command | Default | Pass instead |
| --- | --- | --- |
| `parallel-cli search` | `--mode basic`, `--excerpt-max-chars-total 60000` | `--mode fast --excerpt-max-chars-total 12000` |
| `parallel-cli research run` | `-p pro` | `-p core` or `-p base`; `pro` only for real research |
| `parallel-cli enrich run` | `--processor core` (or the suggested one) | `--processor lite`/`base`, and `--dry-run` first |
| `parallel-cli findall run` | `-g core`, `-n 10` | `-g base -n 10`; the CLI has no `preview` generator, so use the REST API for a $0.10 test |
| `parallel-cli monitor create` | `-f 1d`, `--processor lite` | keep these; avoid `1h` |

Use `--no-wait` with `status`/`poll` for long runs; polling is free. Exit codes: 0 success, 2 bad input, 3 auth, 4 API error, 5 timeout.

## MCP

- **Search MCP** (`https://search.parallel.ai/mcp`): `web_search(objective, search_queries, session_id)` and `web_fetch(urls, objective, search_queries, full_content=false)`. Anonymous use is free and forced to `fast`. Keep `full_content` off; one 10-result search returned about 56 KB.
- **Task MCP** (`https://task-mcp.parallel.ai/mcp`, API key required): `createDeepResearch`, `createTaskGroup`, `getStatus`, `getResultMarkdown`. The processor `createDeepResearch` uses is not documented, so price it as `pro` or higher and confirm with the user first.
