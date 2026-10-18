# Model-side search on DeepSeek models

Use this route only when the user wants a DeepSeek model to decide what to search and to write the answer itself. For research you are doing, call the Search and Fetch APIs directly: they are cheaper, faster, controllable, and return URLs you can cite.

Sources: [Anthropic API guide](https://api-docs.deepseek.com/guides/anthropic_api), [Responses API guide](https://api-docs.deepseek.com/guides/responses_api), [Claude Code integration](https://api-docs.deepseek.com/quick_start/agent_integrations/claude_code), [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing). Live notes are from 2026-10-18.

## Route choice

| Route | Models | Status | Live result |
| --- | --- | --- | --- |
| Anthropic format, `POST https://api.deepseek.com/anthropic/v1/messages` with the `web_search_20250305` server tool | `deepseek-flash`, `deepseek-v4-pro` | Documented: `server_tool_use` and `web_search_tool_result` blocks are supported | Worked on both models |
| Responses format, `POST https://api.deepseek.com/responses` with `{"type": "web_search"}` | `deepseek-v4-pro` only | Documented as **ignored** for all built-in tools | `deepseek-v4-pro` still searched; `deepseek-flash` silently skipped the tool and answered from stale knowledge |

Prefer the Anthropic-format route. Treat Responses-format search as undocumented legacy behaviour that can disappear without notice, and never use it with `deepseek-flash`.

## Anthropic-format request

```bash
curl -sS https://api.deepseek.com/anthropic/v1/messages \
  -H "x-api-key: $DEEPSEEK_API_KEY" -H "anthropic-version: 2023-06-01" -H "content-type: application/json" \
  -d '{
    "model": "deepseek-flash",
    "max_tokens": 1200,
    "tools": [{"type": "web_search_20250305", "name": "web_search"}],
    "messages": [{"role": "user", "content": "What is the latest PostgreSQL 18 minor release and its date? Search the web."}]
  }' | jq '{searches: .usage.server_tool_use.web_search_requests, text: [.content[] | select(.type == "text") | .text]}'
```

Observed response: `thinking`, `server_tool_use` (the queries), `web_search_tool_result` (items with `title`, `url`, and `encrypted_content`), and final `text` blocks. `usage.server_tool_use.web_search_requests` counts the searches.

Live behaviour that differs from Anthropic's own API:

- `max_uses: 1` was ignored: the model still ran 3 searches. Do not use `max_uses` to cap spend.
- `allowed_domains: ["python.org"]` was ignored: results came from 15 hosts. Use the Search API with `site:` when the domain matters.
- `citations` on text blocks was `null`. Collect URLs from the `web_search_tool_result` blocks yourself; the final text may cite inline Markdown links or nothing.
- Claude model names are remapped: `claude-opus-*` runs `deepseek-v4-pro`; `claude-sonnet-*` and `claude-haiku-*` run `deepseek-flash`.

## Responses-format request (deepseek-v4-pro only)

```bash
curl -sS https://api.deepseek.com/responses \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" -H "Content-Type: application/json" \
  -d '{"model": "deepseek-v4-pro", "tools": [{"type": "web_search"}], "input": "Latest PostgreSQL 18 minor release and date?"}' |
  jq '[.output[] | {type, action: .action.type?, query: .action.query?, url: .action.url?}]'
```

Observed: `reasoning`, `web_search_call` items (`search` actions with queries, `open_page` actions with URLs), and a `message`. `annotations` was `[]`. The output leaked internal `ws_call_id=...` pseudo-queries and `#ws_call_id` URL fragments; strip them before showing sources.

Check that a `web_search_call` item exists before trusting the answer. Without one, the model did not search.

## Cost

- Model tokens at the pricing page's rates (per 1M tokens, off-peak and peak): `deepseek-flash` input $0.15 and $0.30 on a cache miss, output $0.60 and $1.20; `deepseek-v4-pro` input $0.66 and $1.32, output $1.98 and $3.96. Peak hours are 01:00-04:00 and 06:00-10:00 UTC on weekdays, excluding Chinese public holidays.
- Searches made by DeepSeek Harness, Claude Code, or Codex on DeepSeek models are free until 00:00 Beijing time on 1 November 2026, then billed at Search API rates. DeepSeek's Claude Code page also notes extra model tokens for summarising results. Whether direct API calls with the server tool are billed per search before November was not verified.
- Live usage on a Sunday (off-peak): Flash with 3 searches used 15,391 uncached input tokens, 9,984 cached, and 582 output tokens in 4.8 s, about $0.003. V4 Pro with 2 searches used 3,114 uncached, 3,200 cached, and 1,011 output tokens in 10.2 s, about $0.004. One direct search costs $0.00075.

## Claude Code on DeepSeek

DeepSeek documents running Claude Code against its Anthropic-format endpoint with `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic` and `ANTHROPIC_AUTH_TOKEN` set to the DeepSeek key, plus model variables such as `ANTHROPIC_MODEL=deepseek-flash[1m]`. Claude Code's built-in web search then runs on DeepSeek's search engine. Follow the official page for the current variable list; do not write the key into shared config files.
