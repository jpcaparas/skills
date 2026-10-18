# API Reference

Use this file for the exact MiniMax search contract: what the endpoint accepts, what it returns, how it fails, and how quota and rate limits work.

Observed live on 2026-10-18. Official sources: the [Web search MCP guide](https://platform.minimax.io/docs/m-plan/mcp-guide), the [error codes](https://platform.minimax.io/docs/api-reference/errorcode), and the open-source [MiniMax-Coding-Plan-MCP](https://github.com/MiniMax-AI/MiniMax-Coding-Plan-MCP) and [`mmx` CLI](https://github.com/MiniMax-AI/cli), which both call this endpoint.

## Hosts and Authentication

| Region | Host | Key source |
| --- | --- | --- |
| Global | `https://api.minimax.io` | minimax.io console |
| Mainland China | `https://api.minimaxi.com` | minimaxi.com console |

Send `Authorization: Bearer $MINIMAX_API_KEY`. A key used on the other region's host returns `2049 "invalid api key"`. The endpoint needs a Token Plan (formerly Coding Plan, now "M Plan") subscription key.

## `POST /v1/coding_plan/search`

```bash
curl -s https://api.minimax.io/v1/coding_plan/search \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q":"rust tokio select cancellation"}'
```

The official MCP server also sends `MM-API-Source: Minimax-MCP`; it is optional.

### Request rules

| Rule | Observed behaviour |
| --- | --- |
| Method | `POST`. `GET`, `PUT`, and wrong paths return HTTP 404 `404 page not found` (plain text) |
| `q` | Required string. `query` is not accepted on its own (`2013`); when both are sent, `q` wins |
| Other keys | Ignored. Tested 34, including Google-style `num`, `gl`, `hl`, `tbs`, `page`, `start`, plus `count`, `limit`, `recency`, `include_domains`, `site`, `type`. Result sets stayed within the controls' normal variation |
| Effective length | First **32 whitespace-separated words** (Google's limit). Words 33 and later, including trailing operators, are silently dropped |
| Hard length | Up to **2,048 characters** (code points, not bytes). 2,049 returns `1033 "system error"`. Bodies up to 4 MB still return HTTP 200 with `1033`, never 413 |
| Odd inputs | `q` in the URL query string or a form-encoded body is also accepted |

### Query operators

| Operator | Result |
| --- | --- |
| `site:domain` | Filters (10/10 results from the domain) |
| Second `site:` or `site:a OR site:b` | Only the first site is used |
| `-site:domain` | Excludes; several work together |
| `"exact phrase"` | Filters |
| `-term` | Filters |
| `intitle:word` | Filters |
| `after:YYYY-MM-DD` | Filters by recency |
| `before:YYYY-MM-DD` | Mostly filters (one stray recent result seen) |
| `filetype:pdf` | Mostly filters (5 of 7 PDFs vs 1 of 9 without) |
| `inurl:`, `OR` between terms | Weak or unclear |

### Response shape

```json
{
  "organic": [
    {"title": "tokio/src/macros/select.rs at master", "link": "https://github.com/...", "snippet": "/// Be aware that cancelling ...", "date": ""}
  ],
  "related_searches": [{"query": "tokio cancellation token"}],
  "base_resp": {"status_code": 0, "status_msg": "success"}
}
```

| Field | Observed behaviour |
| --- | --- |
| `organic` | 5–10 items, never more than 10. No pagination |
| `title`, `link` | Always present. Links can carry tracking parameters such as `srsltid` |
| `snippet` | ~120–170 characters. There is no page text |
| `date` | Often `""`; otherwise relative ("4 hours ago") or absolute ("Jul 30, 2025") |
| `related_searches` | 8 items or none (none for news, URL, single-letter, and long queries) |

Responses are 3–3.5 KB. Identical queries repeated in sequence returned different orderings and sometimes different link sets: in 10 runs, 8 links were always present and 12 appeared in total.

### Errors

MiniMax reports most failures as **HTTP 200** with a nonzero `base_resp.status_code`. Always check it.

| Scenario | HTTP | `base_resp` | Costs quota |
| --- | --- | --- | --- |
| Missing, invalid, or non-`Bearer` key | 200 | `1004 "login fail: Please carry the API secret key in the 'Authorization' field ..."` | No |
| Key from the other region | 200 | `2049 "invalid api key"` | No |
| Missing `q`, non-string `q`, invalid JSON, array body, `text/plain` body | 400 | `2013 "invalid params"` | No |
| `q` is `""` or `null`; over 2,048 characters | 200 | `1033 "system error"` | No |
| Search with no results | 200 | `1027 "output new_sensitive"` | Not measured |
| Burst above the per-minute rate | 200 | `1002 "rate limit exceeded(RPM)"` | No |
| Sustained heavy burst | 200 | `2062 "Token Plan rate limit reached: Upgrade your Token Plan or switch to pay-as-you-go API usage."` | No |
| 5-hour usage exhausted (documented) | 200 | `2056 "usage limit exceeded"` | — |
| Whitespace-only `q` | 200 | `0`, with 10 unrelated results | Yes |

`1027` appeared for `site:example.invalid`, quoted nonsense, and some long or repetitive queries. Unquoted gibberish still returned 9–10 loose matches.

No rate-limit or quota headers are sent. Useful headers: `Trace-Id` and `Minimax-Request-Id` for support requests.

## `GET /v1/api/openplatform/coding_plan/remains`

Undocumented but used by MiniMax's own tooling. Free.

```bash
curl -s https://api.minimax.io/v1/api/openplatform/coding_plan/remains \
  -H "Authorization: Bearer $MINIMAX_API_KEY" | jq '.model_remains[] | select(.model_name=="general")'
```

Each `model_remains` entry has `model_name` (`general`, `video`, ...), the 5-hour window (`start_time`, `end_time`, `remains_time` in milliseconds, `current_interval_remaining_percent`, `current_interval_total_count`, `current_interval_usage_count`, `current_interval_status`) and the weekly window (`weekly_start_time`, `weekly_end_time`, `weekly_remains_time`, `current_weekly_remaining_percent`, ...).

### How searches are counted

- Searches draw on the `general` bucket, which models also use. The count fields stayed at 0; only `current_interval_remaining_percent` moved.
- About **50 successful searches per 1%** of the 5-hour window (71 → 62 over about 450 searches). The weekly percentage stayed at 100.
- 400 (`2013`) and `1033` responses did not move the percentage.

### Rate limits

- Behaves like a token bucket of about **45 requests**, refilling at about **0.875 per second (~52 per minute)**.
- 20 concurrent requests: 17 succeeded, 3 returned `1002`. 50 more immediately: 3 succeeded, 44 `1002`, 3 `2062`. 100 at concurrency 50: all `2062`, clearing after 11–23 seconds.
- Pacing at one request every 1.1–1.25 seconds produced no throttling over about 350 calls.
- MiniMax's FAQ says rate limits are separate from usage limits and usually recover within about a minute.
