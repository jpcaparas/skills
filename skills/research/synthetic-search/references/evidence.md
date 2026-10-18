# Evidence and Verification Limits

This is a **2026-10-18 UTC snapshot** from one Synthetic account, not a promise about every plan or future release. Sources: the official [search](https://dev.synthetic.new/docs/synthetic/search), [quotas](https://dev.synthetic.new/docs/synthetic/quotas), [API overview](https://dev.synthetic.new/docs/api/overview), [rate limits](https://synthetic.new/rate-limits), and [pricing](https://synthetic.new/pricing) pages, plus Synthetic's open-source [Octofriend](https://github.com/synthetic-lab/octofriend) client.

## What the docs say

- `POST https://api.synthetic.new/v2/search` with `{ "query": "..." }`, described as zero-data-retention web search for coding agents and still under development.
- The response example shows `url`, `title`, `text`, and `published`.
- `/quotas` does not count against subscription limits.
- Every plan lists "Web Search API". No page publishes a per-plan search limit, a result count, query length limits, or extra parameters.

## What Octofriend and public clients send

Octofriend (`source/tools/tool-defs/web-search.ts`) sends only `{ query }` with a bearer token and reads `url`, `title`, `highlights`, and `published`. Its commit history replaced `text` with `highlights`. Four independent public MCP and CLI clients also send only `query`; their result-count and length options are applied locally.

## Executed live probes

All probes used the account's own key from the environment. Raw responses stayed in a scratch directory and were not committed.

| Probe | Requests | Result |
| --- | --- | --- |
| Baseline query | 1 | 200 in 1.46 s, 142 KB, 5 results with `url`, `title`, `text`, `highlights`; `published` absent |
| 39 extra body keys on a cached query | 40 | All byte-identical to the baseline |
| Domain, count, date, and type keys on never-seen queries (key sent first, then control) | 12 | Same URL sets; one first-fetch ordering swap reproduced as jitter in a 6-call follow-up |
| `site:`, `-site:`, multiple `site:`, `site:` with path, `site:` subdomain | 9 | All behaved as filters |
| `filetype:pdf`, quotes, `-term`, `OR`, `intitle:` | 5 | Accepted; `filetype:` did not filter; others not reliable filters |
| Tail-marker truncation test (`site:github.com` after filler) | 14 | Honoured at 4,096 characters; ignored at 4,097, 4,110, 4,150, 4,200 |
| Multibyte variant (2,000 CJK characters, 4,976 UTF-8 bytes) | 2 | Filter honoured, so the limit counts characters, not bytes |
| Query length sweep and bisection | 28 | 100,000 characters accepted; 100,001 and larger returned blank 500 |
| Error shapes (auth variants, missing, non-string, array body, empty, whitespace, invalid JSON, content types, GET, wrong paths) | 18 | See `references/api.md` |
| Quota accounting (bad auth ×3, missing ×3, empty ×2, whitespace ×1, success ×1) | 10 | +0, +0, +2, +1, +1; oversized 500s also counted (+4 for 4) |
| 20 concurrent distinct queries | 20 | All 200; per-request 1.63–2.11 s; 2.27 s wall; result counts all 5 |
| Content size over those 20 responses (100 results) | 0 | Responses 50–604 KB; `text` 76–534,088 characters (median 8,740); exactly 1 highlight each (76–8,151 characters); `published` on 16 |
| Gibberish query, unindexed URL, indexed URLs | 6 | Always 5 results; indexed URLs returned first; unindexed URL did not |
| Same-day freshness ("latest AI news this week") | 1 | Pages dated 2026-10-17 and 2026-10-18 |
| Repeat determinism | 9 | Byte-identical bodies within minutes |
| `/quotas` before and after | many | Only `search.hourly.requests` moved; `subscription.requests` stayed 0; weekly credits unchanged |

## Quota exhaustion and reset

Run deliberately near the window's end so search was unavailable for about six minutes.

| Step | Observation |
| --- | --- |
| 06:36 UTC, 182/250 used | Sent the remaining 68 searches at concurrency 10: all `200` |
| At 250/250 | Three more searches: `429`, `{"error":"You've used up your hourly quota for the search API"}`, ~0.27 s, no `Retry-After` or rate-limit headers |
| Counter after the 429s | Still 250, so rejected searches are not counted |
| Missing `query` while over quota | `400 .query is missing`, so validation runs before the quota check |
| Other buckets after 250 searches | `subscription.requests` 0, weekly credits `$131.87` of `$132.00` (unchanged from the start), rolling five-hour 2750/2750 |
| 5 s after `renewsAt` (06:42:29) | `requests` 0; `renewsAt` read as one hour from now; next search `200` |
| First search after reset | `renewsAt` pinned to one hour after that search (07:42:36) |
| Second search 20 s later | `renewsAt` unchanged apart from millisecond jitter, so the window is fixed, not rolling |
| Helper while exhausted | `scripts/search.js` printed the 429 body, a stop hint, and `Search quota renews at 2026-10-18T06:42:29.909Z.`, then exited 1 |

## Not tested

- Behaviour on other plans, or whether 250 per hour differs by plan.
- Long-term determinism and how quickly the index refreshes beyond same-day news.
- Whether invalid-JSON and form-body 500s count against quota.
- Concurrency above 20 simultaneous requests.
- Result quality across languages beyond spot checks in Japanese and French.
