# Patterns

Copy-ready commands for common MiniMax search tasks. Replace `<skill-dir>` with this skill's directory.

## Agent Default: Compact Results

```bash
node <skill-dir>/scripts/search.js --compact "fastapi background tasks lifespan"
```

The output holds `title`, `link`, `date`, and `snippet` per result plus related searches. Use related searches as ideas for follow-up queries.

## Scope With Operators

```bash
node <skill-dir>/scripts/search.js --compact --site github.com "tokio select cancellation"
node <skill-dir>/scripts/search.js --compact --exclude-site medium.com --exclude-site dev.to "rust error handling thiserror anyhow"
node <skill-dir>/scripts/search.js --compact '"cancel safety" tokio after:2026-01-01'
node <skill-dir>/scripts/search.js --compact 'kubernetes pod disruption budget filetype:pdf'
```

MiniMax honours only one `site:`. To cover several sites, run one search per site:

```bash
for site in docs.rs github.com users.rust-lang.org; do
  node <skill-dir>/scripts/search.js --compact --site "$site" "tokio select cancellation"
done
```

## Fan Out Without Tripping the Rate Limit

Run up to about 10 searches in parallel; the helper retries `1002` and `2062` responses, which are free.

```bash
dir=$(mktemp -d)
i=0
for q in "bun startup benchmark" "deno startup benchmark" "node startup time comparison"; do
  i=$((i + 1))
  node <skill-dir>/scripts/search.js --compact "$q" > "$dir/$i.json" &
done
wait
jq -s '[.[].results[]] | unique_by(.link) | map({title, link})' "$dir"/*.json
```

For more than about 40 searches, run them in sequence or pace at about one per second.

## Raw `curl` and `jq` (no Node)

```bash
curl -s https://api.minimax.io/v1/coding_plan/search \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg q 'python requests session retries' '{q: $q}')" \
  | jq 'if .base_resp.status_code != 0 then .base_resp else [.organic[] | {title, link, date, snippet}] end'
```

Build the body with `jq -n --arg` so quotes in the query are escaped. Check `base_resp.status_code` before reading `organic`: errors return HTTP 200.

## Helper Modes

| Flag | Output |
| --- | --- |
| default | Title, URL, date when present, snippet, then related searches |
| `--compact` | JSON: `query`, `results` (`title`, `link`, `date`, `snippet`), `related_searches` |
| `--json` | Raw API response |
| `--urls` | One URL per line |
| `-n` / `--limit` | Caps printed results only |
| `--site`, `--exclude-site` | Append `site:` (once) and `-site:` (repeatable) |
| `--retries <n>` | Retries after `1002`/`2062` with 5 s, 15 s, 30 s back-off (default 3) |

Exit codes: 2 for local validation failures (no request sent), 1 for API errors, 0 otherwise, including zero results.

## Quota Check

```bash
node <skill-dir>/scripts/search.js quota
node <skill-dir>/scripts/search.js quota --json
```
