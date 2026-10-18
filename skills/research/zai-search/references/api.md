# API Reference

Use this file for the exact Z.ai search contracts: the three MCP servers, the REST search and reader endpoints, the free account endpoints, error codes, and how calls are billed.

Observed live on 2026-10-18 with a GLM Coding Plan (Max) key on the international host. Official sources: the [Web Search API](https://docs.z.ai/api-reference/tools/web-search), [Web Reader API](https://docs.z.ai/api-reference/tools/web-reader), [Web Search MCP](https://docs.z.ai/devpack/mcp/search-mcp-server), [Web Reader MCP](https://docs.z.ai/devpack/mcp/reader-mcp-server), [Zread MCP](https://docs.z.ai/devpack/mcp/zread-mcp-server), [pricing](https://docs.z.ai/guides/overview/pricing), and [error codes](https://docs.z.ai/api-reference/api-code). The quota and balance endpoints are undocumented.

## Hosts and Authentication

All calls use `Authorization: Bearer $Z_AI_API_KEY` against `https://api.z.ai/api`. The coding base URL (`/api/coding/paas/v4`) serves the same REST tools at the same cash price; it does not move REST calls onto plan quota. The mainland China platform (`open.bigmodel.cn`) was not tested; the helper accepts `ZAI_API_ROOT` to point elsewhere.

## Billing: which budget each route spends

| Route | Budget | Measured cost |
| --- | --- | --- |
| MCP `web_search_prime`, `webReader`, Zread tools | Coding Plan monthly `TIME_LIMIT` tool quota (4,000 on Max) | One quota unit per successful call; balance drift ≤ $0.0002 per call |
| REST `search_engine: search-prime` | Cash balance | $0.01 per call (also on the coding base URL) |
| REST `search_pro_sogou` | Cash balance | $0.01 per call |
| REST `search_std` | Cash balance | about $0.0015 per call |
| REST `/paas/v4/reader` | Cash balance | $0.01 per call |
| Quota and balance reads | Free | — |

These costs were measured with a key created before 2026-10-16, which Z.ai now classifies as **Compatible**: billing follows the endpoint. Per the [API key management guide](https://docs.z.ai/devpack/notice/api-key-management), keys created since then are billed by **key type** on every supported endpoint: Standard keys spend balance (even in coding tools), Coding Plan keys spend plan quota. So a Standard key may pay cash for MCP calls, and a new Coding Plan key may spend quota on REST. Neither case was tested; compare `quota` and the balance before and after one call to confirm.

Throttled (`1302`) calls consumed neither quota nor cash. The coding plan overview describes newer credit-based plans that charge 1.2 credits per MCP tool call, with 5-hour credits of 2k / 12k / 28k and weekly credits of 10k / 60k / 140k for Lite / Pro / Max, and peak hours Mon–Fri 14:00–18:00 UTC+8. The tested account showed the older per-call `TIME_LIMIT` counter instead; read `quota` rather than assuming which scheme applies.

## MCP servers (streamable HTTP)

| Server | URL | Tools |
| --- | --- | --- |
| Web search | `https://api.z.ai/api/mcp/web_search_prime/mcp` | `web_search_prime` |
| Web reader | `https://api.z.ai/api/mcp/web_reader/mcp` | `webReader` |
| Zread | `https://api.z.ai/api/mcp/zread/mcp` | `search_doc`, `get_repo_structure`, `read_file` |

Each call needs an MCP session: POST `initialize`, keep the `Mcp-Session-Id` response header, POST `notifications/initialized`, then `tools/call` with that header. Without the session the server answers with a misleading `-401 Api key not found`. Replies arrive as `text/event-stream` `data:` lines.

Tool results are text blocks whose text is **JSON encoded twice**: search returns a JSON string containing a JSON array, and reader returns a JSON string containing an object. Zread returns a JSON string containing Markdown-like text. Decode the outer string first.

### `web_search_prime`

| Argument | Observed behaviour |
| --- | --- |
| `search_query` (required) | Schema advises ≤70 characters. Empty → `-400 search_query cannot be empty`. Rewritten by an intent model before searching |
| `search_recency_filter` | `oneDay`, `oneWeek`, `oneMonth`, `oneYear`, `noLimit`; changes results. Invalid values are silently accepted |
| `location` | `cn` (default) or `us`; `us` gives English-web results for English queries |
| `content_size` | `medium` or `high`; `high` made no measurable difference |
| `search_domain_filter` | Accepted and ignored (identical results) |

Results: 6–10 items with `title`, `link`, `content` (~150 characters), and `refer`. No date, site name, or icon.

### `webReader`

Arguments: `url` (required), `timeout` (seconds), `no_cache`, `return_format` (`markdown` or `text`), `retain_images`, `no_gfm`, `keep_img_data_url`, `with_images_summary`, `with_links_summary`. Only `url` and `no_cache` showed an effect; `return_format: text` and `with_links_summary` returned the same content, and `timeout: 1` did not fail a cached page.

Result object: `title`, `description`, `url`, `content` (Markdown), `metadata`, `external`. Measured: an arXiv PDF, a JavaScript-rendered pricing page, and GitHub blob pages all returned text; the Python asyncio docs returned 49.7k characters; PEP 8 returned 50.3k. A redirecting URL returned content but no title. A 404 or dead host fails with `1234` "Network error" after up to ~10 s; a non-URL fails with `-400`.

### Zread

| Tool | Arguments | Notes |
| --- | --- | --- |
| `search_doc` | `repo_name` (`owner/repo`), `query`, `language` (`en`/`zh`) | Searches zread.ai's generated wiki, issues, and commits. Hits look like `:[1]: <title>` with `<excerpt>` blocks; no hits returns only a header and a zread.ai link |
| `get_repo_structure` | `repo_name`, optional `dir_path` | Directory listing |
| `read_file` | `repo_name`, `file_path` | Whole file; a 593 KB TypeScript file came back untruncated. A missing path returns non-error text `code: 1015 ... does not exist` |

Only repositories indexed on zread.ai work (encode/httpx, vitejs/vite, psf/requests, synthetic-lab/octofriend did). Others fail every tool with `1210` "repo not found".

## REST `POST /api/paas/v4/web_search`

```bash
curl -s https://api.z.ai/api/paas/v4/web_search \
  -H "Authorization: Bearer $Z_AI_API_KEY" -H "Content-Type: application/json" \
  -d '{"search_engine":"search-prime","search_query":"vite 8 release notes","count":10,"search_recency_filter":"oneMonth"}'
```

| Field | Observed behaviour |
| --- | --- |
| `search_engine` (required) | `search-prime`, `search_std`, `search_pro`, `search_pro_sogou`, `search_pro_quark`, `search_pro_jina`. Missing → 400 `1214`; unknown → 400 `1211` |
| `search_query` (required) | Missing or empty → 400 `1214`. A 5,000-character query and a numeric query were accepted |
| `count` | Accepted 1–100; `search-prime` still returned ≤10 and `search_std` ~33–41 regardless |
| `search_recency_filter` | `oneDay` returned only pages published the previous or same day |
| `search_domain_filter` | Accepted and ignored on every engine, including `search_pro_jina` |

Response: `id`, `created`, `request_id`, `search_intent` (the rewritten query and intent), and `search_result` items with `title`, `link`, `content`, `media`, `icon`, `refer`, `publish_date`. `search_std` excerpts reach ~5,000 characters. The Sogou and Quark engines favour Chinese-language web pages.

## REST `POST /api/paas/v4/reader`

Body `{"url": ...}` plus the same options as `webReader`; returns `reader_result` with the page content. $0.01 per call. Missing `url` → 400 `1214`. Prefer the MCP reader when a Coding Plan exists.

## Free account endpoints (undocumented)

| Endpoint | Returns |
| --- | --- |
| `GET /api/monitor/usage/quota/limit` | `level` and `limits`: `TIME_LIMIT` (`usage` cap, `currentValue`, `remaining`, `nextResetTime` ms, `usageDetails` per `search-prime` / `web-reader` / `zread`) and `TOKENS_LIMIT` (`percentage` of the 5-hour token window) |
| `GET /api/biz/account/query-customer-account-report` | `availableBalance` in USD |
| `GET /api/biz/subscription/list` | Subscriptions on the account |
| `GET /api/monitor/usage/tool-usage?startTime=...&endTime=...` | Tool usage history |

## Error codes

| Code | Where | Meaning |
| --- | --- | --- |
| `1000` / `1001` | REST 401 | Bad key / missing auth |
| `1113` | REST | Insufficient cash balance |
| `1210` | Zread `-400` | Repository not indexed ("repo not found") |
| `1211` | REST 400 | Unknown `search_engine` |
| `1214` | REST 400 | Missing or invalid required parameter |
| `1234` | Reader | Page fetch failed (404, dead host, timeout) |
| `1301` | Search | Content filter rejected the query |
| `1302` | MCP `-429` | Rate limit; clears within seconds |
| `1305` | Any | Service overloaded |
| `1308` / `1310` | Any | Usage limit reached until reset |

MCP tool failures arrive as `isError: true` results whose text starts `MCP error -<status>:` followed by a JSON body with the code.

## Rate limits and latency

- MCP concurrency 2, 3, and 5: no errors. Concurrency 8: 10 of 24 calls `1302`; 10: 17 of 30; 12: 24 of 36. Twenty sequential searches took 58 s with no errors.
- MCP search 0.7–3 s; reader 1–2.5 s for live pages, up to ~10 s for failures; REST search 1.5–10 s.
