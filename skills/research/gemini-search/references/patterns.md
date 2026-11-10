# Gemini search patterns

The helper reads `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) and never prints it.

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
