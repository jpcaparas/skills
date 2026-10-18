# Gotchas

Use this file when Synthetic Search output surprises you. Each item was reproduced live on 2026-10-18 unless marked otherwise.

## 1. Body parameters do nothing

**Symptom:** `numResults`, `includeDomains`, `startPublishedDate`, `type`, or similar keys have no effect, and the API returns no error.

**Cause:** the endpoint reads only `query` and silently drops other keys.

**Fix:** use query operators (`site:`, `-site:`) for scope and run more queries for more results.

## 2. Long queries are cut at 4,096 characters without warning

**Symptom:** a long query ignores its ending, often a trailing `site:` filter.

**Cause:** only the first 4,096 characters are searched. Queries up to 100,000 characters are accepted; longer ones return a blank `500`.

**Fix:** keep queries short and put operators within the first 4,096 characters. The helper rejects longer queries locally.

## 3. Blank 500s still cost quota

**Symptom:** `500 Internal Server Error` with an empty body.

**Cause:** an empty `query` string, a query over 100,000 characters, or a body that is not valid JSON. The first two were confirmed to consume a unit of the hourly search quota.

**Fix:** validate before sending. The helper rejects blank queries. Missing or non-string `query` returns a free `400` with a useful message.

## 4. Whitespace queries return unrelated news

**Symptom:** `{"query":"   "}` returns `200` with five front-page news results.

**Fix:** trim and reject blank queries before sending. The call is billed.

## 5. There is never a "no results" response

**Symptom:** a nonsense or very narrow query still returns 5 results.

**Fix:** check each result's title, URL, and highlight for relevance. Refine or narrow the query rather than presenting weak matches.

## 6. `text` is the whole page

**Symptom:** a single response is hundreds of kilobytes and floods the context window.

**Cause:** `text` holds the full page as Markdown; the largest seen was 534,088 characters.

**Fix:** read `highlights` first (`--compact`), save the raw response (`--save`), and extract a page's `text` with `jq` only when needed.

## 7. `published` is usually missing

**Symptom:** results have no date.

**Cause:** `published` is present on only a minority of results (16 of 100 sampled). The docs example implies it is always present.

**Fix:** treat it as optional. Do not infer recency from rank; look for dates inside `text` or ask a narrower, time-scoped query.

## 8. `highlights` exists but is not documented

Results include a `highlights` array with one query-relevant excerpt. Synthetic's own client, Octofriend, reads `highlights` instead of `text`. Prefer it for summaries, but tolerate its absence in case the field changes.

## 9. URL queries are index lookups, not fetches

A URL query returns that page first only when it is already indexed. Otherwise you get pages that merely mention similar words. Verify result 1 matches the URL before relying on it.

## 10. `filetype:` and quoted phrases are not filters

`filetype:pdf` returned HTML pages. Quotes and `-term` may influence ranking but did not reliably filter. Only `site:` and `-site:` behaved as filters.

## 11. Quota and window behaviour

**Symptom:** `429 {"error":"You've used up your hourly quota for the search API"}`, with no `Retry-After` header.

**Cause:** the hourly search bucket is a hard cap in a fixed window that starts at the first search; `renewsAt` does not slide. It is separate from subscription requests and weekly credits, which 250 searches left untouched.

**Fix:** stop searching and report `search.hourly.renewsAt` from `/quotas` (the helper prints it automatically). Retrying is harmless to the counter but pointless until the window renews. Plan large fan-outs against the remaining quota first.

## 12. The API is still under development

Fields and limits may change. When a behaviour matters, re-run `scripts/probe_synthetic_search.py --mode limits` and compare with `references/evidence.md` before relying on it.
