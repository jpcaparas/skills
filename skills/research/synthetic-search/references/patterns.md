# Patterns

## Raw `curl` and `jq` (no Node)

Compact projection that keeps context small:

```bash
curl -s https://api.synthetic.new/v2/search \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg q 'python requests session retries' '{query: $q}')" \
  | jq '[.results[] | {title, url, published, highlight: .highlights[0][0:1200]}]'
```

Build the body with `jq -n --arg` so quotes and newlines in the query are escaped correctly.

URLs only:

```bash
curl -s https://api.synthetic.new/v2/search \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" \
  -d '{"query":"nix flake tutorial"}' | jq -r '.results[].url'
```

Titles with URLs:

```bash
curl -s https://api.synthetic.new/v2/search \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" \
  -d '{"query":"rust async await"}' | jq -r '.results[] | "\(.title)\t\(.url)"'
```
