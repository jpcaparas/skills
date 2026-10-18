# DeepSeek search gotchas

Each item was observed live on 2026-10-18 unless marked as documented only.

## Dates are a day early in UTC

Every non-null `date` was `T16:00:00+00:00`, which is midnight in Beijing (UTC+8). PostgreSQL 18.6 came back as `2026-08-12T16:00:00+00:00`, but its release notes say `Release date: 2026-08-13`. Add 8 hours before taking the date part. The helper's `published` field does this. Reading the raw value as a UTC date shifts every date one day early and can put a page on the wrong side of a cutoff.

About one third of results have `date: null`. Undated is not the same as old; fetch the page when the date matters.

## Year-only `after:` excludes the whole year

`after:2025` returned pages from 2026. `after:2026` returned zero results in October 2026, because it means after 2026 ends. Write full dates (`after:2026-01-01`) or use the helper's `--after 2026`, which expands to that. `before:2019` behaves as expected (before 1 January 2019).

An invalid date in `after:` was silently ignored, which widens the search instead of failing. The helper rejects impossible dates before sending.

## Junk queries still cost money

Billing depends on whether results came back, not on whether they were relevant. Gibberish returned 10 results, which makes it billable under the documented rule. A quoted phrase that exists nowhere also returned 10 unrelated, billable results. Only empty result sets are free: unknown `lang:` codes, parentheses, and impossible date windows returned `[]`.

Check that results match the query before building an answer on them, especially for quoted error messages.

## `OR` lets one site take every slot

`site:github.com OR site:docs.rs` returned only GitHub results. The union is real but ranking decides the mix. Run one query per site when each source matters (`references/patterns.md`).

Parentheses are not supported: `(a OR b) site:x` returned nothing.

## The 128-character limit includes operators

The limit counts Unicode code points across the whole query string, operators included. A 115-character query plus ` site:github.com` fails. Keep the topic short and let operators carry the filtering, or split the question into several searches.

## Fetched Markdown is backslash-escaped

Fetch escapes Markdown punctuation in all content, including JSON and plain text: `2026\-08\-13`, `\{\"slideshow\"\:`. Quoting it verbatim produces wrong code, versions, and URLs. The helper reverses CommonMark escapes of ASCII punctuation; `--raw` keeps the original. The reversal turns `\\` into `\`, which matters only for content that itself contained escaped backslashes.

## Fetch fails on PDFs and images

arXiv PDFs, PNGs, target 404 or 500 pages, dead hosts, `localhost`, and `169.254.169.254` all return `404 failed to fetch URL`. These are free but give no detail. For PDFs, search for an HTML version (an arXiv abstract page, a docs mirror) or use another tool.

JavaScript-heavy apps can return partial content without an error. If a fetched page looks thin, say so instead of treating it as complete.

## Fetch requests look Chinese to target sites

Target servers saw a Firefox on Linux user agent with `Accept-Language: zh-CN`. Sites that negotiate language may return Chinese pages. Fetch the explicit language URL (for example `/en/`).

## Summaries and snippets are longer than documented

Docs say snippets are 100-200 characters and summaries 600-800. Live snippets reached about 2,000 characters and summaries 4,600. Ten raw results are about 40 KB, so use `--compact` or `jq` instead of dumping raw JSON into context.

## Duplicate pages under different fragments

About a quarter of URLs carried `#fragments`, and one page could appear several times. The helper merges results that differ only by fragment. Query strings are kept because they often identify different pages.

## Scores rarely separate results

`rerank_score` values across ten results often sit within 0.3 of each other, and most results have `authority` 3 or 4. Use them as a tiebreaker, not as a relevance filter.

## Localization changes results more than expected

Without `localization`, results for local-intent queries ("bank", "weather forecast") were not US-oriented; every IP tried, including 8.8.8.8, changed nearly all results. Pass `--loc` with an address in the user's region for local questions.

## Throttling is per account and fast

Search and Fetch each allow 5 requests per second for the whole account. Any parallel agents using the same account share that budget. `429` responses have no `Retry-After` header and are not billed. Do not launch more than about four requests per second in total.

## Balance updates lag

The balance moved in whole cents, minutes after the calls. It cannot attribute individual requests; use the helper's `billable_requests` count and the list price for estimates.
