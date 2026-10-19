# Gemini search patterns

Run the helper from the skill directory: `node scripts/gemini_search.js <command>`. It reads `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) and never prints it.

## Helper recipes

```bash
# Grounded answer with resolved sources, queries, coverage, and cost
node scripts/gemini_search.js search "Is the Vite 8 environment API stable yet?"

# Machine-readable summary for an agent
node scripts/gemini_search.js search --json "What did the latest Kubernetes release deprecate?" |
  jq '{grounded, coverage, queries, sources: [.sources[].url]}'

# One site only (prompt-level site: plus local flagging of off-site sources)
node scripts/gemini_search.js search --site docs.rs "tokio select cancellation safety"

# Tighter budget: one query
node scripts/gemini_search.js search --max-queries 1 "Current RBNZ official cash rate"

# Sharper queries for a hard lookup, still ungated
node scripts/gemini_search.js search --model gemini-3.8-flash "Exact release dates of Go 1.27.0 and 1.27.1"

# Read specific pages (no search fee; page tokens bill as input)
node scripts/gemini_search.js read --ask "List the breaking changes." https://vite.dev/guide/migration.html
node scripts/gemini_search.js read --ask "Summarise the abstract." https://arxiv.org/pdf/1706.03762
```

Exit codes: `0` ok, `1` API error, `2` refused or invalid input (nothing was sent), `3` ungrounded answer, `4` no URL could be read.

## Search, then read

1. `search` to find candidate sources and a first answer.
2. If coverage is low or the question needs detail, `read` the two or three best resolved URLs with a precise `--ask`.
3. Cite the resolved URLs.

Search plus URL context in one call did not make the model read pages, so keep the two steps separate.

## Lists and comparisons

Batch entities in groups of about five and run calls in parallel (the measured project handled 30 grounded calls at once; lower tiers throttle sooner, and the helper retries 429):

```bash
for group in "PostgreSQL, MySQL, SQLite" "Redis, Valkey, KeyDB" "Kafka, Redpanda, NATS"; do
  node scripts/gemini_search.js search --json "Latest stable version and release date of each: $group" > "/tmp/gs-$(echo "$group" | tr -cd 'a-zA-Z').json" &
done; wait
jq -s 'map({grounded, coverage, queries: (.queries | length)})' /tmp/gs-*.json
```

## Dates, regions, and freshness

The API ignores location and time filters, so state them in the question: "published since 2026-10-12 (today is 2026-10-19)", "for savers in New Zealand". The model then writes dated or regional queries ("Kubernetes news October 12 2026 to October 19 2026").

## Structured output

Do not combine `responseSchema` with search on generateContent: grounding metadata disappears. Use the Interactions API, which keeps search steps and the billable count. Structured output made Flash-Lite search more (6 queries on two uncapped runs, versus 2 for the same question in prose), so keep a cap in `system_instruction` and check the count (capped at 2, it ran 1 and then 4):

```bash
curl -sS https://generativelanguage.googleapis.com/v1beta/interactions \
  -H "x-goog-api-key: $GEMINI_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-3.1-flash-lite",
    "store": false,
    "system_instruction": "Ground every answer in Google Search results: always search first. Use at most 2 search queries.",
    "tools": [{"type": "google_search"}],
    "response_mime_type": "application/json",
    "response_format": {"type": "object", "properties": {"version": {"type": "string"}, "release_date": {"type": "string"}}},
    "input": "Latest PostgreSQL 18 minor release and its date?"
  }' | jq '{searches: .usage.grounding_tool_count, out: [.steps[] | select(.type == "model_output") | .content[0].text]}'
```

## curl and jq (generateContent)

```bash
curl -sS "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" -H "Content-Type: application/json" \
  -d '{
    "systemInstruction": {"parts": [{"text": "Ground every answer in Google Search results: always search first. Use at most 3 search queries."}]},
    "contents": [{"role": "user", "parts": [{"text": "What changed in PostgreSQL 18.6?"}]}],
    "tools": [{"google_search": {}}]
  }' > /tmp/gs.json
jq '.candidates[0].groundingMetadata.webSearchQueries' /tmp/gs.json
jq -r '.candidates[0].groundingMetadata.groundingChunks[].web.uri' /tmp/gs.json | sort -u |
  while read -r u; do curl -sS -o /dev/null -w '%{redirect_url}\n' -I "$u"; done
```

## Streaming

`:streamGenerateContent?alt=sse` streams text, but `groundingMetadata` arrives only in the final event (first event about 1.8 s, final 1.9 s for a short answer). Buffer citations until the stream ends.

## Showing results to end users

If an app shows grounded answers to people, the Gemini API terms require displaying the Search Suggestions in `searchEntryPoint.renderedContent` (or the Interactions `search_suggestions` HTML). Agent-internal research does not render them.
