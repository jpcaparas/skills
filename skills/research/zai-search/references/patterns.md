# Patterns

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
