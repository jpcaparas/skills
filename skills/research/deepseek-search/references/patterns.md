# DeepSeek search patterns

Run the helper from the skill directory: `node scripts/deepseek_search.js <command>`. Every command reads `DEEPSEEK_API_KEY` and never prints it.

## Helper recipes

```bash
# Readable results, ten by default
node scripts/deepseek_search.js search "rust 1.95 release notes"

# Compact JSON for an agent; trims summaries and snippets to 600 characters
node scripts/deepseek_search.js search --compact -c 20 "kubernetes gateway api vs ingress"

# Only URLs, for piping into fetch
node scripts/deepseek_search.js search --urls -n 3 --site docs.python.org "asyncio taskgroup exceptions"

# Date window: --after 2026 expands to after:2026-01-01
node scripts/deepseek_search.js search --compact --after 2026-09-01 --before 2026-10-18 "postgresql security release"

# Several sites, a language, and an exclusion
node scripts/deepseek_search.js search --compact --site docs.rs --site github.com --lang en --exclude-site reddit.com "tokio select"

# Keep everything the API returned, then inspect locally
node scripts/deepseek_search.js search --save /tmp/ds-raw.json --compact "vite 8 environment api"
jq -r '.results[] | [.rerank_score, .authority, .url] | @tsv' /tmp/ds-raw.json

# Fetch one page; the full page goes to the file
node scripts/deepseek_search.js fetch --save /tmp/page.md https://vite.dev/guide/migration.html

# Free balance check, with remaining request capacity
node scripts/deepseek_search.js balance
```

## curl and jq

```bash
curl -sS https://api.deepseek.com/v1/tools/search \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" -H "Content-Type: application/json" \
  -d '{"query": "postgresql 18.6 release site:postgresql.org", "count": 5}' |
  jq -r '.results[] | "\(.date // "undated")\t\(.url)\t\(.title)"'

curl -sS https://api.deepseek.com/v1/tools/fetch \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" -H "Content-Type: application/json" \
  -d '{"url": "https://www.postgresql.org/docs/18/release-18-6.html"}' |
  jq -r .content | sed -E 's/\\([][!"#$%&'"'"'()*+,./:;<=>?@\\^_`{|}~-])/\1/g' > /tmp/page.md
```

Raw `curl` output keeps the Beijing-midnight dates and backslash escapes; convert them as `references/gotchas.md` describes, or use the helper.

## Research workflow

1. One broad query, then two to four narrower ones: product plus version, error text in quotes, a site-restricted query for primary sources.
2. Read `summary` fields first. They are long and written for models, so many questions need no fetch.
3. Fetch two or three primary sources (release notes, docs, the original announcement) before stating facts, versions, or dates.
4. Cite the URLs you used. Prefer pages with `authority` 3 or 4, but do not trust the score alone: most results score 3 or 4.

## Fan-out

`batch` validates every query first, starts four per second, retries throttles, and merges URLs seen in earlier queries:

```bash
node scripts/deepseek_search.js batch --compact -c 5 \
  "bun 1.3 release notes" "bun 1.3 node compatibility" "bun 1.3 benchmark"

printf '%s\n' "deno 2.5 release" "deno 2.5 npm compatibility" > /tmp/queries.txt
node scripts/deepseek_search.js batch --compact --file /tmp/queries.txt
```

The JSON output lists `runs[]` per query, `unique_urls`, `duplicates_removed`, and `billable_requests`; stderr shows the list-price cost. When several agents or shells share one account, they share the same 5 QPS budget, so keep combined traffic below it.

## Balanced multi-site coverage

`site:a OR site:b` lets the higher-ranked site take every result. When each source matters, run one query per site in a single paced batch:

```bash
node scripts/deepseek_search.js batch --compact -c 5 \
  "tokio select cancellation site:docs.rs" "tokio select cancellation site:github.com"
```

## Chinese-language and regional research

- Chinese sources appear often, even for English queries (an English Python-release question surfaced ithome.com, 163.com, and pythonlang.cn). Query in Chinese for Chinese topics, and add `--lang zh` or `--lang zh,en` when language matters. `lang:zh` alone still returned some English pages.
- For English-only results on a mixed topic, use `--lang en`; it worked even for a CJK query.
- Results are not US-centric by default. For local intent (banks, weather, shops, laws), pass `--loc` with an IP address in the user's region; for technical queries the effect is smaller.
- Fetch requests reach targets with a Firefox on Linux user agent and `Accept-Language: zh-CN`, so multilingual sites may serve Chinese pages. Fetch the language-specific URL when one exists.

## Choosing count and content

- The price is per request, so `-c 20` costs the same as `-c 1`. Raise `count` for breadth instead of running more queries; lower it to keep output small.
- `--content` returns page text for every result and roughly triples the response. Use it when you need most results' full text in one call; otherwise fetch the two or three best URLs.

## Estimating spend

- Each successful search or fetch costs $0.00075 at list price. A 20-query fan-out plus 10 fetches costs about $0.02.
- Check `balance` before and after large jobs. Debits appear in whole cents after a delay of minutes, so small jobs may not move it.
