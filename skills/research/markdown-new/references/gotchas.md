# Gotchas

These are the non-obvious behaviors that mattered in live testing on April 9, 2026.

## 1. GitHub `blob` URLs are a trap

Symptom:

- markdown.new returns huge HTML-ish output instead of the file contents.

Cause:

- `blob` URLs are webpage views, not raw file URLs.

Fix:

- Convert the URL to `raw.githubusercontent.com/...` before sending it to markdown.new.

## 2. POST is safer than GET for complex target URLs

Symptom:

- URLs with their own query strings are awkward in GET path-prefix mode.
- A fully percent-encoded target URL returned HTTP 400 in testing.

Cause:

- The outer markdown.new request also uses query parameters such as `format=json`, so nested query strings are brittle in the path.

Fix:

- Use `POST /` with `{"url":"https://target.example/path?x=1&y=2"}`.

## 3. Bare domains normalize, arbitrary paths do not

Symptom:

- `example.com` worked.
- `not-a-url` returned HTTP 500.

Cause:

- markdown.new appears willing to add `https://` for domain-like input, but it does not rescue arbitrary non-URL strings.

Fix:

- Send a full URL when possible.
- If you accept user input, normalize it before calling the service.

## 4. Invalid `method` values do not fail loudly

Symptom:

- `{"method":"bogus"}` still succeeded.

Cause:

- The service appears to fall back instead of rejecting invalid values.

Fix:

- Validate `method` client-side if the caller actually cares whether the path is `auto`, `ai`, or `browser`.

## 5. `method` is not trustworthy provenance

Symptom:

- A direct Markdown endpoint still reported `Cloudflare Workers AI`.

Cause:

- The response metadata may describe the winning branch loosely, or the pipeline may not surface exact provenance.

Fix:

- Treat the returned Markdown as the main signal.
- Do not build policy around the `method` field alone.

## 6. Error reporting is weak

Symptom:

- Missing `url`, malformed JSON, percent-encoded path failures, bogus crawl status IDs, and invalid non-URL paths all returned 400 or 500 without a useful response body in testing.

Cause:

- The service appears to close error responses without detailed diagnostics.

Fix:

- Validate obvious bad inputs before sending them.
- Log the HTTP status code and request shape on your side.

## 7. `tokens` is not guaranteed

Symptom:

- Successful browser-mode conversions omitted `tokens` in testing.

Cause:

- Different code paths return slightly different JSON shapes.

Fix:

- Treat `tokens` as optional.
- If budgeting matters, fall back to your own token estimate.

## 8. `x-rate-limit-remaining` is documented but was not observed

Symptom:

- The FAQ says to check `x-rate-limit-remaining`.
- Successful tests did not include that header.

Cause:

- The documentation may be ahead of the deployed service, or the header may be inconsistent.

Fix:

- Do not depend on the header existing.
- Track request counts on the caller side if rate budgeting matters.

## 9. Crawl limits are inconsistent across pages

Symptom:

- One homepage section says 100 pages.
- The dedicated crawl page says 500 pages and documents `limit` up to 500.

Cause:

- Marketing copy and crawl documentation are out of sync.

Fix:

- Quote the dedicated crawl page when you need the current documented limit.
- Flag the inconsistency for users who need certainty.

## 10. Crawl cache is real, and delete may fail

Symptom:

- Starting the same crawl returned a cached job from April 3, 2026.
- `DELETE /crawl/status/<jobId>` on that cached completed job returned HTTP 500.

Cause:

- Crawl jobs are cached and the delete path does not appear robust for completed cached jobs.

Fix:

- Do not rely on delete as cleanup.
- Use `maxAge` or the UI's `Re-crawl` when freshness matters.

## 11. Public URLs only still matters

Symptom:

- The docs explicitly exclude paywalled or authenticated pages.

Cause:

- markdown.new fetches URLs like a public client and does not carry your session or cookies by default.

Fix:

- Use markdown.new only for public content.
- If auth is required, use a different fetch path that can carry credentials.

## 12. The homepage UI is less deterministic than the HTTP interface

Symptom:

- In browser automation, the crawl page worked end-to-end but the homepage `Convert` form did not navigate in one session.

Cause:

- Client-side UI behavior is more fragile than direct HTTP calls.

Fix:

- Prefer the raw endpoint patterns for automation.
- Keep the UI pages for human use or when the user explicitly wants the browser experience.

## 13. Successful conversions can still be too large to use directly

Symptom:

- markdown.new returns valid Markdown, but the result is so large that it is a poor fit for an agent prompt or context window.

Cause:

- Some public pages are dense reference documents or giant encyclopedia articles.

Evidence:

- `https://react.dev/reference/react/useEffect` returned about 14k tokens in testing.
- `https://en.wikipedia.org/wiki/Alan_Turing` returned about 74k tokens in testing.

Fix:

- Narrow the target URL before conversion.
- Prefer a more specific subsection page when one exists.
- If the page is still huge, convert it first and then summarize or slice it before handing it to another model.

## Quick fallback rules

If a request looks even slightly tricky:

1. Use `POST /` instead of GET path-prefix mode.
2. Use raw file URLs, not page views.
3. Treat response fields beyond `success`, `url`, `title`, and `content` as optional.
4. Expect status-code-only failures and log enough context to retry safely.
5. Treat huge successful conversions as a separate failure mode and trim them before use.
