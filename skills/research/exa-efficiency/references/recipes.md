# Cheap Routes, Copy-Ready

Each recipe is the lowest-cost way to do one job. Price anything beyond a single `lite` search or `/contents` call first:

```bash
C="python3 <skill-dir>/scripts/exa_cost.py"
$C estimate agent/runs body.json --budget-usd 1   # exit 0 ok, 2 warn, 3 blocked
```

REST examples assume:

```bash
E=https://api.exa.ai
AUTH="x-api-key: $EXA_API_KEY"
JSON="Content-Type: application/json"
```

Write responses to files and read them with `jq`. Every Search, Contents, and Answer response carries `costDollars.total`; Agent runs carry `costDollars` and `usage`. Report those, not the estimate.

## Table of Contents

- [Search](#search)
- [Read chosen pages](#read-chosen-pages)
- [Synthesized answers](#synthesized-answers)
- [Deep search](#deep-search)
- [People and companies](#people-and-companies)
- [Agent runs](#agent-runs)
- [Monitors](#monitors)
- [SDKs](#sdks)
- [MCP](#mcp)

## Search

```bash
curl -sS -X POST "$E/search" -H "$AUTH" -H "$JSON" -d '{
  "query": "PostgreSQL 18 release notes on logical replication changes",
  "type": "lite",
  "numResults": 10,
  "contents": {"highlights": {"maxCharacters": 1500}}
}' > search.json
jq -r '.results[] | [.url, .title, (.publishedDate // "")] | @tsv' search.json
jq '.costDollars.total' search.json   # 0.004
```

Write the query as a description of the ideal page, not keywords. Use `includeDomains` or `startPublishedDate` when the user needs a source or recency; both work on `lite`. Switch to `type: "auto"` only for `summary`, `maxAgeHours`, `outputSchema`, `systemPrompt`, `extras`, or `stream`; `lite` returns 400 for those, even when set to `false` or `[]`.

Freshness: `lite` serves cached pages and drops results with no cached copy. When the page must be current, use `auto` with `"contents": {"highlights": true, "maxAgeHours": 0}` (same price, about 9 s slower).

## Read chosen pages

```bash
curl -sS -X POST "$E/contents" -H "$AUTH" -H "$JSON" -d '{
  "urls": ["https://www.postgresql.org/docs/release/18.0/"],
  "highlights": {"query": "logical replication changes", "maxCharacters": 2000}
}' > contents.json
jq -r '.results[0].highlights[]' contents.json; jq -c '.statuses' contents.json
```

$0.001 a URL for each content type, up to 100 URLs. There is no `contents` wrapper here: options sit next to `urls`. With no option the endpoint returns full text (45 KB for that page). When the whole page is the deliverable, send `"text": {"maxCharacters": 20000}` instead of highlights, not both. Failed URLs appear in `statuses` with an error tag and are not billed.

## Synthesized answers

A cited short answer, $0.005:

```bash
curl -sS -X POST "$E/answer" -H "$AUTH" -H "$JSON" \
  -d '{"query": "Which PostgreSQL version introduced the pg_stat_io view?"}' > answer.json
jq -r '.answer, (.citations[] | .url)' answer.json
```

Leave `text` off: `true` inlined 278 KB of source text. Every `model` value cost $0.005.

A structured answer with field-level grounding, $0.007, from `auto` search:

```bash
curl -sS -X POST "$E/search" -H "$AUTH" -H "$JSON" -d '{
  "query": "PostgreSQL 18 logical replication changes",
  "type": "auto",
  "outputSchema": {"type": "object", "required": ["changes"],
    "properties": {"changes": {"type": "array", "maxItems": 5, "items": {"type": "string"}}}}
}' > synth.json
jq '.output.content, .output.grounding' synth.json
```

`outputSchema` allows at most 10 properties in total and 2 levels of nesting, and adds about 2 s.

## Deep search

```bash
curl -sS -X POST "$E/search" -H "$AUTH" -H "$JSON" -d '{
  "query": "AI infrastructure companies that raised a Series A or B in the last six months",
  "type": "deep-lite",
  "additionalQueries": ["AI infra Series B 2026", "GPU cloud startup funding round"],
  "outputSchema": {"type": "object", "required": ["companies"], "properties": {"companies": {
    "type": "array", "maxItems": 8, "items": {"type": "object", "required": ["name", "round", "amount"],
      "properties": {"name": {"type": "string"}, "round": {"type": "string"}, "amount": {"type": "string"}}}}}}
}' > deep.json
```

$0.012 for `deep-lite` (about 2 s live) or `deep` (5–7 s). `additionalQueries` cost nothing extra. Do not use legacy `deep-reasoning` ($0.015); use `deep`, or Agent for long multi-hop work.

## People and companies

```bash
curl -sS -X POST "$E/search" -H "$AUTH" -H "$JSON" \
  -d '{"query": "site reliability engineers in Wellington", "type": "lite", "category": "people", "numResults": 10}'
```

`category: "company"` and `"people"` bill at the type's price. They reject published-date filters, and `people` rejects `excludeDomains`. Results are 2–7 KB each; keep `numResults` small.

## Agent runs

Known scope, fixed price:

```bash
cat > run.json <<'EOF'
{"query": "Does redbarnrobotics.com have a public pricing page?",
 "effort": "low",
 "outputSchema": {"type": "object", "required": ["verdict", "source"],
   "properties": {"verdict": {"type": "string", "enum": ["present", "absent", "cannot_verify"]},
                  "source": {"type": "string"}}}}
EOF
python3 <skill-dir>/scripts/exa_cost.py estimate agent/runs run.json --budget-usd 0.05
curl -sS -X POST "$E/agent/runs" -H "$AUTH" -H "$JSON" -d @run.json > created.json
RUN=$(jq -r .id created.json)
until jq -e '.status | IN("completed","failed","cancelled")' run-status.json >/dev/null 2>&1; do
  sleep 3; curl -sS "$E/agent/runs/$RUN" -H "$AUTH" > run-status.json   # polling is free
done
jq '{stopReason, costDollars, output: .output.structured}' run-status.json
```

Unknown scope, such as list building: send `"effort": "auto", "budget": {"maxCostDollars": 1}` and raise the cap only with the user's agreement. A run that hits the cap is billed the cap and stops with `stopReason: "budget_reached"`. Fixed efforts reject `budget` with a 400. `POST /agent/runs/{id}/cancel` discards results; `/stop` (keep partial results) works only on `ultra`.

## Monitors

```bash
cat > monitor.json <<'EOF'
{"name": "PostgreSQL 19 beta",
 "search": {"query": "PostgreSQL 19 beta release announced", "numResults": 5, "contents": {"highlights": true}},
 "webhook": {"url": "https://hooks.example.org/exa"}}
EOF
python3 <skill-dir>/scripts/exa_cost.py estimate monitors monitor.json   # monthly_usd
curl -sS -X POST "$E/monitors" -H "$AUTH" -H "$JSON" -d @monitor.json > monitor-created.json
MON=$(jq -r .id monitor-created.json)
curl -sS -X POST "$E/monitors/$MON/trigger" -H "$AUTH"           # one paid run
curl -sS "$E/monitors/$MON/runs" -H "$AUTH" | jq '.data[0]'       # output, no cost field
curl -sS -X DELETE "$E/monitors/$MON" -H "$AUTH"                  # stops billing; irreversible
```

The webhook must be a public HTTPS URL; create returns 400 without one. Without a `trigger` the monitor only runs when triggered; it did not run at creation. Add `"trigger": {"type": "interval", "period": "1d"}` (about $0.45 a month) only after agreeing a delete date; `1h` is about $10.80 a month per monitor. Pause with `PATCH /monitors/{id}` `{"status": "paused"}`.

## SDKs

```python
from exa_py import Exa  # pip install exa-py; reads EXA_API_KEY

exa = Exa()
result = exa.search("PostgreSQL 18 logical replication changes", type="lite", num_results=5,
                    contents={"highlights": True})
pages = exa.get_contents(["https://www.postgresql.org/docs/release/18.0/"], highlights=True)
```

Pass `type` and `contents` every time; SDK defaults have changed between releases. Tool-calling helpers in Exa's docs use `type="auto"` and the Python SDK caps `get_contents` text at 10,000 characters.

## MCP

- Hosted server: `https://mcp.exa.ai/mcp`. Keyless use is free and rate-limited; add `x-api-key` or connect with OAuth (`?login`) for higher limits at API prices.
- `web_search_exa(query, objective, numResults)` runs `auto` with highlights. 5 results returned about 8 KB live. Describe the ideal page in `query` and the facts you need in `objective`. Prefix `category:people` or `category:company` for those indexes.
- `web_fetch_exa(urls, maxCharacters)` returns text capped at 3,000 characters by default.
- `?tools=` replaces the default tool set. `web_search_advanced_exa` exposes summaries, freshness, and subpages, which are cost-adding knobs; `agent_run` needs authentication and defaults to `low`.
- The local `exa-mcp-server` can set `DEFAULT_SEARCH_TYPE=lite`; the hosted server cannot.
