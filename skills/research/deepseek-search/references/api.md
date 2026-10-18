# DeepSeek Search and Fetch API contract

Official sources: [Search & Fetch guide](https://api-docs.deepseek.com/guides/search), [Models & Pricing](https://api-docs.deepseek.com/quick_start/pricing). "Live" notes are from the 2026-10-18 spike in `references/evidence.md`.

## Authentication and hosts

| Item | Value |
| --- | --- |
| Base URL | `https://api.deepseek.com` (the helper honours `DEEPSEEK_API_ROOT` for tests) |
| Headers | `Authorization: Bearer $DEEPSEEK_API_KEY`, `Content-Type: application/json` |
| Search | `POST /v1/tools/search` |
| Fetch | `POST /v1/tools/fetch` |
| Balance | `GET /user/balance` (free) |

The same key works for models, Search, and Fetch. There is no separate search key or plan.

## Search request

| Field | Type | Default | Rules (live-verified) |
| --- | --- | --- | --- |
| `query` | string | required | 1-128 Unicode code points including operators. 128 emoji pass; 129 ASCII or CJK characters return `400 'query' must be at most 128 characters`. Empty or whitespace-only returns `400 'query' must not be empty`; a missing or `null` query returns a serde-style `400` |
| `count` | integer | `10` | 1-50. `0` and `51` return `400 'count' must be between 1 and 50`; `"5"`, `5.0`, and `-1` return `400 Invalid JSON request: invalid type...` |
| `ori_question` | string or null | none | 1-128 characters; `null` means not provided. Changes ranking (about 43% overlap with the plain query in one probe) but did not resolve ambiguous terms |
| `localization` | string | `""` | Must parse as an IPv4 or IPv6 address, otherwise `400` |
| `need_content` | boolean | `false` | Non-booleans return `400`. When `false`, `content` is always `""` |

Unknown fields are ignored without error.

### Query operators

| Operator | Documented | Live behaviour |
| --- | --- | --- |
| `site:example.com` | Restrict to a site | Strict: every result on the site. Path prefixes work (`site:github.com/tokio-rs`) |
| `site:a OR site:b` | Several sites | Union, but ranking decides the mix: github.com plus docs.rs returned only GitHub; docs.rs plus stackoverflow.com mixed 5 and 15 |
| `-site:example.com` | Exclude a site | Worked |
| `"exact phrase"` | Exact match | 10 of 10 results contained an existing phrase. A phrase that exists nowhere still returned 10 unrelated, billed results |
| `-term`, `-"phrase"` | Exclude | Worked (`jaguar -car` returned the animal; `-"release notes"` removed the phrase) |
| `lang:en`, `lang:zh,en` | Restrict languages | `lang:en` worked on a CJK query; `lang:zh` mixed languages; unknown codes such as `lang:xx` returned 0 results |
| `after:YYYY-MM-DD`, `before:YYYY-MM-DD` | Date window | Honoured, inclusive of the Beijing date. Invalid dates were silently ignored |
| `after:YYYY`, `before:YYYY` | Year forms | `after:2025` meant from 2026; `after:2026` returned nothing in October 2026. `before:2019` meant before 2019-01-01 |
| `( ... )` | Not documented | Returned 0 results |

## Search response

`200 {"results": [...]}`. A search with no matches returns `"results": []` (not billed).

| Field | Type | Notes |
| --- | --- | --- |
| `title`, `url` | string | About 25% of URLs carried `#fragments`; one page can appear several times under different fragments |
| `snippet` | string | Documented as 100-200 characters; live 150 to about 2,000 |
| `summary` | string | Written for models; documented 600-800 characters, live 1,600-4,600 |
| `content` | string | Only with `need_content: true`; up to 28,800 characters per result seen; no cap |
| `site_name`, `site_icon` | string or null | `site_icon` is a DeepSeek CDN URL |
| `date` | string or null | RFC 3339. Every non-null value was `T16:00:00+00:00`: midnight Beijing time. Add 8 hours to get the publication date. About one third were `null` |
| `rerank_score` | number | Documented 0-3, with 1.5 or more counted as high quality. Live values clustered tightly (for example 2.02-2.29 across ten results), so they rank but rarely separate good from bad |
| `authority` | integer | 0-4, `-1` unknown; 3 or more is authoritative. Most results scored 3 or 4 |

Repeating the same request returned identical results.

## Fetch request and response

Request: `{"url": "<http or https URL>"}`. The URL needs a host, at most 8,192 characters, and no username or password.

Response: `200 {"title": "...", "content": "<Markdown>"}`. `title` is often `""` for non-HTML pages. Content escapes Markdown punctuation with backslashes (`\-`, `\.`, `\:`, `\{`, `\"`). Plain text and JSON targets are escaped too.

## Errors and retries

Errors use the OpenAI format: `{"error": {"message": "... (request_id: <uuid>)", "type": "invalid_request_error", "param": null, "code": "invalid_request_error"}}`. Keep the `request_id` when reporting problems to DeepSeek.

| Status | Meaning | Action |
| --- | --- | --- |
| 400 | Invalid header, JSON, or field | Fix the request; do not retry unchanged |
| 401 | Missing or invalid key | Check `DEEPSEEK_API_KEY` |
| 402 | Insufficient balance | Top up; do not retry |
| 403 | Fetch rejected by security policy | Choose another URL |
| 404 | Fetch could not produce Markdown: unavailable URL, site policy, target error, unsupported type such as PDF or image, or nothing extractable | Try another source; not billed |
| 408 | Reading the request body timed out | Retry with backoff |
| 413 | Body too large | Shrink the request |
| 429 | Search or Fetch QPS exceeded | Retry with backoff; pace below 5 per second |
| 500, 504 | Internal error or downstream timeout | Retry with backoff |

Live `429` bodies said "Too many requests. Please pace your requests reasonably..." and carried no `Retry-After` header. The helper waits about 1, 2.5, then 5 seconds.

## Billing

- $0.75 per 1,000 successful Search requests and the same for Fetch (the Chinese docs list ¥5 per 1,000).
- Billable means HTTP 200 with a non-empty `results` array, or Fetch content. Empty searches, errors, and timeouts are free. `count` does not change the price.
- Search and Fetch called by DeepSeek Harness, Claude Code, or Codex on DeepSeek models are free until 00:00 Beijing time on 1 November 2026, then billed per request.
- Deductions come from the granted balance first, then the topped-up balance. Live debits appeared in whole cents and lagged by minutes, so the balance is a coarse spend meter.

## Rate limits

- Search 5 QPS and Fetch 5 QPS per account, independent of each other, shared by every key on the account, and separate from model concurrency limits.
- Fetch also has an undisclosed per-domain limit. Five concurrent fetches to one domain all succeeded in the spike.
- Live: 15 simultaneous searches gave 5 successes and 10 `429`s; 8 gave 5 and 3. Fetch bursts behaved the same.

## Balance

`GET /user/balance` returns `{"is_available": true, "balance_infos": [{"currency": "USD", "total_balance": "2.63", "granted_balance": "0.00", "topped_up_balance": "2.63"}]}`. Amounts are strings.
