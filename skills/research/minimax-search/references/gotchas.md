# Gotchas

Use this file when MiniMax search output surprises you. Each item was reproduced live on 2026-10-18.

## 1. Errors arrive as HTTP 200

**Symptom:** a 200 response with no `organic` array.

**Cause:** MiniMax reports auth failures, rate limits, and server errors in `base_resp.status_code`.

**Fix:** check `base_resp.status_code` is `0` before reading results. The helper does this.

## 2. "output new_sensitive" usually means no results

**Symptom:** `1027 "output new_sensitive"`.

**Cause:** the search found nothing, for example `site:example.invalid` or a quoted phrase that appears nowhere.

**Fix:** treat it as zero results and broaden the query. The helper returns an empty list.

## 3. Long queries lose their ending

**Symptom:** a trailing `site:` filter or keyword has no effect.

**Cause:** only the first 32 words are searched. Over 2,048 characters returns `1033`.

**Fix:** keep queries short and put operators early. The helper rejects queries over 32 words.

## 4. Only one `site:` counts

**Symptom:** `site:a.com OR site:b.com` returns only `a.com` results.

**Fix:** run one search per site and merge results.

## 5. Bursts are throttled

**Symptom:** `1002 "rate limit exceeded(RPM)"` or `2062 "Token Plan rate limit reached ..."`.

**Cause:** about 45 requests can burst, then about 52 per minute are allowed.

**Fix:** keep parallel batches small and retry after a short wait. Throttled calls are free. `2062` does not mean the plan is exhausted; it clears within a minute.

## 6. No count, page, locale, or date parameters

**Symptom:** `num`, `page`, `gl`, `hl`, `tbs`, `count`, or `recency` change nothing.

**Fix:** use operators such as `after:` and `before:` for dates, and more queries for breadth. Results are US English; add the language or country to the query text when it matters.

## 7. Snippets only

**Symptom:** results are too short to answer from.

**Fix:** open the promising links with a reader or fetch tool.

## 8. Results are not stable

**Symptom:** the same query returns a different order or a few different links.

**Fix:** do not rely on rank. Merge several queries; repeat a query when completeness matters.

## 9. Region mismatch looks like a bad key

**Symptom:** `2049 "invalid api key"` with a key that works elsewhere.

**Fix:** match `MINIMAX_API_HOST` to the key's region (`api.minimax.io` global, `api.minimaxi.com` mainland).

## 10. Whitespace queries are billed

`"   "` returns 10 unrelated results and counts as a search. Trim queries; the helper rejects blank ones.
