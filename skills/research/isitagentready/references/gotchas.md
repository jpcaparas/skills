# Gotchas

## 1. Do not claim the official level from source code alone

Cloudflare's scan returns `level` and `levelName` for a deployed URL. Without that runtime result, write a repository assessment and say the official level is unverified.

## 2. Inspection order is not evidence quality

Honor an explicit browser-first request; otherwise choose the order that resolves uncertainty and allow independent source/runtime work. Browser-usability claims still require rendered browser evidence. A source-only audit must remain labelled source-only.

## 3. A signal can exist in source and still fail in production

This often means:

- the route is not deployed
- a CDN or proxy strips the header
- the content type is wrong
- a framework rewrite shadows the intended path

Investigate deployment drift or exposure failure, but do not treat the scanner as infallible. Its result is authoritative for what it reported at that time, not every deployed behavior. Preserve disagreements with direct HTTP/browser evidence and compare request context, timing, and target before concluding.

## 4. `llms.txt` is not a substitute for markdown negotiation

Cloudflare's April 2026 default score checked markdown negotiation. Regardless of scoring changes, `llms.txt` and `llms-full.txt` do not prove that `Accept: text/markdown` works.

## 5. AI bot rules require named crawler blocks

Cloudflare's April 2026 `ai-rules` baseline expected named crawler entries rather than only `User-agent: *`. Verify current scanner criteria and official crawler identifiers when needed; do not weaken deliberate bot restrictions to improve a score.

## 6. Web Bot Auth is easy to over-penalize

If the site does not send bot or agent requests to other sites, the official scan may treat Web Bot Auth as informational or neutral. Preserve that nuance.

## 7. `.well-known` documents may be generated dynamically

Do not conclude a discovery artifact is missing just because there is no static file on disk. Check route handlers, middleware, Workers, proxy config, and build generators.

## 8. WebMCP is a runtime behavior

Client-side source hits are useful clues, but the signal is most credible when confirmed in a rendered browser session.

## 9. Commerce scoring is version-dependent

Cloudflare's April 17, 2026 blog described x402, UCP, and ACP as checked but non-scoring. Record the measured scan/version rather than hardcoding that result into future reports. Do not let non-applicable commerce capabilities dominate a non-commerce audit.

## 10. Split frontend and backend repos can overstate readiness

If the authoritative production URL is a public web app but the repository also contains a separate API app, backend OpenAPI or MCP packages are not enough for a pass. Count them as source evidence only until the public runtime exposes or links the discovery surface.

## 11. Keep absolute workstation paths out of the report

Use repo-relative paths such as `apps/web/app/robots.ts` in the markdown report. Reserve absolute local paths for machine-local metadata only when they are genuinely necessary.

## 12. A scanner is a third-party disclosure

Get consent before submitting private, staging, internal, or credential-bearing URLs. Never forward credentials or signed tokens. Direct authorized checks and a labelled source assessment are valid alternatives; an audit does not authorize writes, access-control bypasses, or relaxed security headers.
