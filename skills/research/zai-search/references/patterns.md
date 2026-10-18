# Patterns

Use this file for ready commands. Resolve `scripts/zai.js` from the skill directory. The helper needs Node.js 18+ and reads `Z_AI_API_KEY` (or `ZAI_API_KEY`).

## Check budget first (free)

```bash
node scripts/zai.js quota          # plan level, tool calls left and reset time, cash balance
node scripts/zai.js quota --json   # raw quota and balance payloads
```

If `quota` reports no Coding Plan, every search must use `--rest` and costs cash. Ask before spending.

## Research loop

```bash
node scripts/zai.js search --compact "postgres advisory lock patterns"
node scripts/zai.js search --compact --recency oneMonth "bun 2 release"
node scripts/zai.js search --urls --site docs.rs "select! cancel safety"
node scripts/zai.js read --chars 8000 https://docs.rs/tokio/latest/tokio/macro.select.html
node scripts/zai.js read --save /tmp/select.md https://docs.rs/tokio/latest/tokio/macro.select.html
```

- Output modes: readable (default), `--compact` (normalised JSON), `--urls` (one link per line), `--json` (raw payload, unfiltered by `--site`). `-n` limits printed results only.
- `--site domain` appends `site:domain` and drops off-domain results locally, reporting how many it dropped on stderr. If few remain, rephrase the query rather than repeating it.
- Search summaries are ~150 characters. Read the two or three most relevant pages before answering.
- For breadth, run several distinct phrasings, then merge by URL; one query returns at most ~10 results.

## Parallel fan-out

Keep at most about five MCP calls in flight; eight or more trigger `1302` throttling. The helper retries `1302` three times (after 3, 8, and 15 s); throttled calls are free.

```bash
printf '%s\n' "tokio select cancellation" "tokio cancellation token" "tokio graceful shutdown" |
  xargs -P 4 -I{} node scripts/zai.js search --urls "{}" | sort -u
```

## GitHub repositories with Zread

```bash
node scripts/zai.js repo-search vitejs/vite "how does HMR propagate updates"
node scripts/zai.js repo-tree psf/requests src/requests
node scripts/zai.js repo-file psf/requests src/requests/sessions.py
```

Zread suits popular repositories indexed on zread.ai. `repo not found` means unindexed; use GitHub directly. An empty `repo-search` means no indexed match; browse with `repo-tree` and `repo-file`.

## REST (cash) when it earns its cost

Use `--rest` only when the user accepts pay-as-you-go cost or has no plan, or needs publish dates, the rewritten query, or many long excerpts.

```bash
node scripts/zai.js search --rest --compact "vite 8 release"                         # search-prime, $0.01, dates
node scripts/zai.js search --rest --engine search_std --compact -n 40 "rust axum"     # ~40 long excerpts, ~$0.0015
node scripts/zai.js search --rest --json "rust axum" | jq '.search_intent'            # see the rewritten query
```

`--count` cannot raise `search-prime` above about 10 results. Use `search_pro_sogou` or `search_pro_quark` for Chinese-language web coverage.

## Raw MCP with curl

```bash
url=https://api.z.ai/api/mcp/web_search_prime/mcp
auth="Authorization: Bearer $Z_AI_API_KEY"
accept="Accept: application/json, text/event-stream"
sid=$(curl -s -D - -o /dev/null "$url" -H "$auth" -H "$accept" -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}' |
  awk -F': ' 'tolower($1)=="mcp-session-id"{print $2}' | tr -d '\r')
curl -s "$url" -H "$auth" -H "$accept" -H "Content-Type: application/json" -H "Mcp-Session-Id: $sid" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}'
curl -s "$url" -H "$auth" -H "$accept" -H "Content-Type: application/json" -H "Mcp-Session-Id: $sid" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"web_search_prime","arguments":{"search_query":"vite 8 release","location":"us"}}}' |
  sed -n 's/^data://p' | jq -r '.result.content[0].text | fromjson | fromjson | .[] | "\(.title)\n\(.link)\n"'
```

## Answering

Cite every claim with a URL from results or read pages. MCP results carry no dates; when freshness matters, use `--recency`, check dates on the read page, or use REST `publish_date`. Say when a claim rests only on a short summary.
