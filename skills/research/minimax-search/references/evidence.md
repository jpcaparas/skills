# Evidence and Verification Limits

This is a **2026-10-18 UTC snapshot** from one global-region Token Plan key, not a promise about every plan or future release.

Sources:
- the official [Web search MCP guide](https://platform.minimax.io/docs/m-plan/mcp-guide), [server tools guide](https://platform.minimax.io/docs/guides/server-tools), [error codes](https://platform.minimax.io/docs/api-reference/errorcode), and M Plan usage and FAQ pages from the [docs index](https://platform.minimax.io/docs/llms.txt);
- the open-source [MiniMax-Coding-Plan-MCP](https://github.com/MiniMax-AI/MiniMax-Coding-Plan-MCP) (`minimax_mcp/server.py`, `client.py`) and [`mmx` CLI](https://github.com/MiniMax-AI/cli) (`src/commands/search/query.ts`), both of which send only `{"q": ...}` to `/v1/coding_plan/search`.

## What the docs say

- The MCP `web_search` tool takes one `query` parameter and "returns search results and related suggestions".
- The CLI source says the endpoint returns at most 10 results and has no pagination.
- The rate-limits page has no entry for search. M Plan pages describe 5-hour and weekly usage windows, rate limits separate from usage limits that "typically [recover] within about one minute", and possible dynamic limits at peak.
- `/docs/token-plan/*` pages now redirect to M Plan pages.

## Executed live probes (search endpoint)

About 1,050 POSTs in total, plus about 22 free quota reads. Raw responses were kept in a scratch directory and not committed.

| Probe | Result |
| --- | --- |
| Baseline (~12 queries) | 5–10 results, never more; fields `title`, `link`, `snippet`, `date`; snippets 123–163 chars; `related_searches` 8 or 0; 2.9–3.5 KB; 1.5–2.2 s |
| 34 extra body keys (68 requests + 6 controls) | No effect beyond control variation (controls alone had pairwise Jaccard 0.54–1.0) |
| Operators (18 queries) | See the operator table in `references/api.md` |
| Tail-marker truncation | `site:github.com` after 31 filler words: 10/10 GitHub; after 32, 33, 40, 60 words: 0/10 |
| Length bisection | 2,048 characters OK, 2,049 → `1033`; same boundary with CJK (2,048 chars = 4,780 bytes OK) |
| Oversized bodies (8 KB–4.2 MB) | HTTP 200 with `1033`, 0.5–2.0 s |
| Input validation (28 cases) | See the error table in `references/api.md` |
| Quota accounting | `general` 5-hour percentage 71 → 62 over the session; controlled run of 150 paced searches moved it 65 → 62 (one point per 50); 200 `2013` and 50 `1033` calls moved nothing; weekly stayed 100 |
| Burst 20 / 50 / 100 | 17 OK + 3 `1002`; 3 OK + 44 `1002` + 3 `2062`; 100 `2062`, cleared in 11–23 s |
| Steady 2/s and 1.5/s after rest | 83 and 111 OK before intermittent `1002`; 1.1–1.25 s pacing gave 0 throttles over ~350 calls |
| Freshness | Results labelled "55 minutes ago"; same-day news returned |
| Locale | French query returned English pages; "coffee shop" rotated between US cities; Japanese and Chinese queries returned native pages |
| Determinism (10 identical queries) | 10 orderings, 2 link sets, 8 links always present, 12 in total |
| Region | Same key on `api.minimaxi.com`: `2049 "invalid api key"` |
| Helper | Live `--site`, `--compact`, `quota`, and 1027-as-empty checks; guards for a second `--site` and 33 words fired without a request |

## Server tool route (13 calls, $0.01 per search when it runs)

MiniMax also documents a server-side `web_search` tool inside chat requests: `{"type":"web_search_20250305","name":"web_search"}` on `POST /anthropic/v1/messages` and `{"type":"web_search"}` on `POST /v1/responses`. It is not a good substitute for direct search:

- MiniMax-M3 searched only when the tool was forced, and even forced calls sometimes did not search. Without searching it gave confident wrong answers about current events.
- MiniMax-M2.7 emitted a client-side `plugin_web_search` tool call instead of running a server search.
- `allowed_domains`, `blocked_domains`, and `user_location` were accepted but ignored. `max_uses: 1` stopped a second search with `stop_reason: pause_turn`.
- When it ran, results matched the direct endpoint (8 of 10 URLs shared) and came back as `web_search_tool_result` blocks with `title`, `url`, `content` (≤168 chars), and optional `page_age`. There was no encrypted content, no citations on text, and no server-tool usage counter.

## Not tested

- Whether server-tool calls on a subscription key bill the $0.01 list price, plan usage, or nothing.
- The meaning of `current_interval_status` and `current_weekly_status` values.
- Daily or weekly search caps, and how the 5-hour percentage behaves at the window reset.
- Whether `site:` with a path restricts to that path, and whether `OR` works between terms.
- Whether `1027` ever signals a real content block rather than zero results.
