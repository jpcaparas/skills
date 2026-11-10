# Patterns

## Raw `curl` and `jq` (no Node)

```bash
curl -s https://api.minimax.io/v1/coding_plan/search \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg q 'python requests session retries' '{q: $q}')" \
  | jq 'if .base_resp.status_code != 0 then .base_resp else [.organic[] | {title, link, date, snippet}] end'
```

Build the body with `jq -n --arg` so quotes in the query are escaped. Check `base_resp.status_code` before reading `organic`: errors return HTTP 200.
