# Patterns

Copy-ready commands for common Synthetic Search tasks. Replace `<skill-dir>` with this skill's directory.

## Agent Default: Compact Results Plus a Saved Copy

```bash
node <skill-dir>/scripts/search.js --compact --save /tmp/synthetic-q1.json "httpx retry transport"
```

Read the highlights first. Pull a full page only when you need it, from the saved file:

```bash
jq -r '.results[] | "\(.title)\t\(.url)"' /tmp/synthetic-q1.json
jq -r '.results[0].text' /tmp/synthetic-q1.json | head -c 20000
```

## Restrict or Exclude Sites

The API ignores domain parameters in the body, so filters go in the query string. The helper appends the operators for you:

```bash
node <skill-dir>/scripts/search.js --site docs.rs --site github.com "tokio select cancellation"
node <skill-dir>/scripts/search.js --site github.com/tokio-rs "select cancellation"
node <skill-dir>/scripts/search.js --exclude-site stackoverflow.com "react useEffect cleanup"
```

The equivalent raw query is `tokio select cancellation site:docs.rs site:github.com`.

## Fan Out for Breadth

One search returns 5 results. For a survey, run several focused queries in parallel and merge them by URL:

```bash
dir=$(mktemp -d)
i=0
for q in "bun startup benchmark" "deno startup benchmark" "node startup time comparison"; do
  i=$((i + 1))
  node <skill-dir>/scripts/search.js --compact "$q" > "$dir/$i.json" &
done
wait
jq -s '[.[].results[]] | unique_by(.url) | map({title, url})' "$dir"/*.json
```

Check `node <skill-dir>/scripts/search.js quotas` first when a fan-out will use more than about 20 searches.

## Look Up a Known URL

When you have a URL and the page is likely indexed, a URL query returns it as result 1, with its Markdown in `text`:

```bash
node <skill-dir>/scripts/search.js --save /tmp/page.json --urls -n 1 "https://docs.astral.sh/uv/concepts/projects/"
jq -r 'select(.results[0].url | startswith("https://docs.astral.sh/uv/concepts/projects")) | .results[0].text' /tmp/page.json
```

Check that result 1 is the requested URL. If it is not, the page is not indexed; use a real fetch tool instead.

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

## Helper Modes

| Flag | Output |
| --- | --- |
| default | Title, URL, `published` when present, highlight (1,200 characters by default) |
| `--compact` | JSON: `query` plus `url`, `title`, `published`, `highlights` per result |
| `--text` / `--content` | Adds each page's full `text`, truncated to `--chars` (5,000 by default) |
| `--json` | Raw API response; often 50–600 KB |
| `--urls` | One URL per line |
| `--titles` | `title<TAB>url` |
| `--save <file>` | Writes the raw response to a file alongside any other mode |
| `-n` / `--limit` | Caps printed results only; the API always returns 5 |
| `--site`, `--exclude-site` | Append `site:` and `-site:` operators; repeatable |

The helper exits with code 2 and makes no request for blank queries, queries longer than 4,096 characters after operators are appended, malformed flags, or a missing key. API failures exit with code 1 and print the status, body, and a hint.

## Quota Checks

```bash
node <skill-dir>/scripts/search.js quotas
node <skill-dir>/scripts/search.js quotas --json
```

## Re-verify Behaviour

```bash
python3 <skill-dir>/scripts/probe_synthetic_search.py --mode limits   # 4 searches: ignored params + 4,096 cut
python3 <skill-dir>/scripts/probe_synthetic_search.py --mode errors   # 1 search: error shapes
python3 <skill-dir>/scripts/probe_synthetic_search.py --mode quotas   # free
```

Run these when results contradict this skill, before changing the skill's documented limits.
