# Patterns

Use this file when you want the fastest working command for a common Synthetic Search workflow.

## Raw Search

```bash
curl -s https://api.synthetic.new/v2/search \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"python requests library documentation"}' | jq .
```

Use this when another agent or script needs the full response object.

## URLs Only

```bash
curl -s https://api.synthetic.new/v2/search \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"nix flake tutorial"}' | jq -r '.results[].url'
```

Use this when the search stage only needs candidate pages.

## Titles With URLs

```bash
curl -s https://api.synthetic.new/v2/search \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"rust async await"}' | jq -r '.results[] | "\\(.title)\\t\\(.url)"'
```

Use this when you want a compact shortlist for humans.

## Human-Readable Helper

`scripts/search.js` merges the best parts of the older local wrapper and the published `skills.sh` examples.

```bash
node scripts/search.js "rust async await"
node scripts/search.js --content --limit 3 --chars 1500 "rust async await"
node scripts/search.js --json "rust async await"
node scripts/search.js --urls "rust async await"
node scripts/search.js --titles "rust async await"
```

### What Each Mode Does

| Mode | Result |
| --- | --- |
| default | Title, URL, optional published, short snippet |
| `--content` | Includes truncated full text |
| `--json` | Prints raw API JSON |
| `--urls` | Prints one URL per line |
| `--titles` | Prints `title<TAB>url` |
| `--limit` / `-n` | Caps displayed items only |

## Quota Checks

```bash
curl -s https://api.synthetic.new/v2/quotas \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" | jq .
```

```bash
node scripts/search.js quotas
node scripts/search.js quotas --json
```

Use these before large batches or when a user asks how much headroom is left.

## Structured Live Probe

```bash
python3 scripts/probe_synthetic_search.py --mode search --query "rust async await"
python3 scripts/probe_synthetic_search.py --mode quotas
python3 scripts/probe_synthetic_search.py --mode errors
python3 scripts/probe_synthetic_search.py --mode all --query "rust async await"
```

Use this when you need a clean JSON report for current behavior instead of eyeballing ad hoc commands.

## Routing Guidance

- If the user wants the exact API surface, stay in raw `curl` mode.
- If the user wants shell-friendly filtering, stay in `jq` mode.
- If the user wants readable terminal output, use `scripts/search.js`.
- If the user is debugging a discrepancy between docs and behavior, run `scripts/probe_synthetic_search.py` and then consult `references/gotchas.md`.
