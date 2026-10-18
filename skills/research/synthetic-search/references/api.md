# API Reference

Use this file for the exact Synthetic Search contract: what the endpoint accepts, what it returns, how it fails, and how the quota works.

Observed against the live API on 2026-10-18. Official docs: [search](https://dev.synthetic.new/docs/synthetic/search) and [quotas](https://dev.synthetic.new/docs/synthetic/quotas). Synthetic labels the API as still under development.

## Base URL and Authentication

```text
https://api.synthetic.new/v2
```

Send `Authorization: Bearer $SYNTHETIC_API_KEY`. The `Bearer ` prefix is mandatory; a raw key or an `x-api-key` header returns `401 {"error":"Authorization header must begin with \"Bearer \"."}`. An unknown key returns `401 {"error":"Invalid API Key."}`.

## `POST /search`

```bash
curl -s https://api.synthetic.new/v2/search \
  -H "Authorization: Bearer $SYNTHETIC_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query":"rust async await"}'
```

### Request rules

| Rule | Observed behaviour |
| --- | --- |
| Method | `POST` only; `GET /v2/search?query=...` returns `405` |
| Body | JSON object. `Content-Type` is optional (`text/plain` also parsed); form encoding returns blank `500` |
| `query` | Required string |
| Other body keys | Silently ignored. Tested 39 keys, including `numResults`, `num_results`, `limit`, `count`, `includeDomains`, `excludeDomains`, `startPublishedDate`, `type`, `category`, `contents`, `text`, `highlights`, `page`, `offset`, `country`, `language`, `livecrawl`. Responses were byte-identical with and without them, including on never-before-seen queries |
| Effective length | First **4,096 characters** (UTF-16 code units, not UTF-8 bytes). Text after that, including trailing `site:` operators, has no effect and gives no warning |
| Accepted length | Up to **100,000 characters**; 100,001 or more returns blank `500` and still costs quota |
| Operators | `site:domain` restricts results and matches subdomains (`site:python.org` returned `packaging.python.org`); `site:domain/path` restricts to a path; several `site:` terms form a union; `-site:domain[/path]` excludes. `filetype:pdf` did not restrict results. Quotes, `-term`, `OR`, and `intitle:` were accepted but are not reliable filters |
| URL as query | Returns that page as result 1 when it is already indexed (raw GitHub URLs map to the `github.com/.../blob/...` page). Unindexed URLs return unrelated pages about the URL text, so this is not a live fetch |

### Response shape

```json
{
  "results": [
    {
      "url": "https://docs.rs/tokio/latest/tokio/macro.select.html",
      "title": "select in tokio - Rust",
      "text": "# select in tokio ... (entire page as Markdown)",
      "highlights": ["Waits on multiple concurrent branches, ..."],
      "published": "2022-01-22T00:00:00.000Z"
    }
  ]
}
```

| Field | Observed behaviour |
| --- | --- |
| `results` | Always exactly 5 entries, including for gibberish queries. There is no empty-result signal |
| `url` | Canonical page URL. Near-duplicates (for example `/en/stable/` and `/en/latest/`) can take separate slots |
| `title` | String; sometimes empty |
| `text` | Whole page converted to Markdown, not a snippet. In a 100-result sample the median was ~8.7k characters and the maximum 534,088. News pages may start with `Published:`, `Source:`, and `Language:` lines |
| `highlights` | Undocumented. Array with exactly one query-relevant Markdown excerpt per result (76–8,151 characters, median ~2.6k). The best default for agent context |
| `published` | Documented, but optional: present on 16 of 100 sampled results, otherwise absent. ISO-8601 when present |

Whole responses ranged from about 30 KB to 604 KB. Identical queries repeated minutes apart returned byte-identical bodies; the first fetch of a new query can order results slightly differently.

### Errors

| Scenario | Status | Body | Counts against quota |
| --- | --- | --- | --- |
| Missing or malformed `Authorization` | `401` | `Authorization header must begin with "Bearer ".` | No |
| Unknown key | `401` | `{"error":"Invalid API Key."}` | No |
| Missing `query` | `400` | `{"error":"Invalid POST body: .query is missing"}` | No |
| Non-string `query` (number, null, array) | `400` | `{"error":"Invalid POST body: .query is not a string"}` | No |
| Body is a JSON array | `400` | `{"error":"Invalid POST body: array is not an object"}` | No |
| `query` is `""` | `500` | Empty | **Yes** |
| Invalid JSON or form-encoded body | `500` | Empty | Not measured |
| `query` longer than 100,000 characters | `500` | Empty | **Yes** |
| Whitespace-only `query` | `200` | Five unrelated news pages | **Yes** |
| Wrong path such as `/v1/search` | `404` | `API route not found: '/v1/search'. ...` | No |
| Hourly search quota exhausted | `429` | `{"error":"You've used up your hourly quota for the search API"}` | No |

Responses carry no rate-limit headers. CORS allows any origin.

## `GET /quotas`

Free: the docs say `/quotas` does not count against subscription limits, and repeated calls did not change any counter.

```bash
curl -s https://api.synthetic.new/v2/quotas -H "Authorization: Bearer $SYNTHETIC_API_KEY" \
  | jq '.search.hourly'
```

```json
{ "limit": 250, "requests": 171, "renewsAt": "2026-10-18T06:42:29.181Z" }
```

The full response also includes `subscription`, `freeToolCalls`, `weeklyTokenLimit`, and `rollingFiveHourLimit`. Read numbers from the live response; limits vary by account and plan, and Synthetic publishes no per-plan search limit.

### How searches are counted

- Each search consumes one unit of `search.hourly` only. `subscription.requests`, weekly credits, and the rolling five-hour limit did not change across about 250 searches.
- The window is fixed, not rolling. With no searches, `renewsAt` reads as one hour from now; the first search pins `renewsAt` to one hour after that search, and later searches do not move it.
- `200` responses and blank `500` responses count; `400` and `401` responses do not.

### Over the quota

The limit is a hard cap. The 251st search in a window returned:

```text
HTTP 429
{"error":"You've used up your hourly quota for the search API"}
```

- No `Retry-After` or rate-limit headers. Read `search.hourly.renewsAt` from `/quotas` to know when to resume.
- `429` responses do not increment the counter, so a stray retry does not dig the hole deeper; still, stop searching until `renewsAt`.
- Validation still runs first: a missing `query` returned `400` while over quota.
- Model endpoints are unaffected because subscription requests and weekly credits are separate buckets.
