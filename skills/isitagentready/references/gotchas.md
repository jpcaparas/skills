# Gotchas

## 1. Do not claim the official level from source code alone

Cloudflare's scan returns `level` and `levelName` for a deployed URL. Without that runtime result, write a repository assessment and say the official level is unverified.

## 2. Browser-first means browser-first

The user explicitly requested that a headless browser pass happen before source-code analysis when a production URL and browser skill are available. Do not treat that as optional ordering.

## 3. A signal can exist in source and still fail in production

This often means:

- the route is not deployed
- a CDN or proxy strips the header
- the content type is wrong
- a framework rewrite shadows the intended path

Call this out as deployment drift or exposure failure, not as "the scan must be wrong."

## 4. `llms.txt` is not a substitute for markdown negotiation

Cloudflare's default score checks markdown negotiation. `llms.txt` and `llms-full.txt` are valuable, but they do not prove that `Accept: text/markdown` works.

## 5. AI bot rules require named crawler blocks

Cloudflare's `ai-rules` skill says a wildcard-only `User-agent: *` policy is insufficient. Search for explicit entries such as `GPTBot`, `Claude-Web`, `Google-Extended`, and the other named bots.

## 6. Web Bot Auth is easy to over-penalize

If the site does not send bot or agent requests to other sites, the official scan may treat Web Bot Auth as informational or neutral. Preserve that nuance.

## 7. `.well-known` documents may be generated dynamically

Do not conclude a discovery artifact is missing just because there is no static file on disk. Check route handlers, middleware, Workers, proxy config, and build generators.

## 8. WebMCP is a runtime behavior

Client-side source hits are useful clues, but the signal is most credible when confirmed in a rendered browser session.

## 9. Commerce is currently non-scoring

Cloudflare's April 17, 2026 blog says x402, UCP, and ACP are checked but do not currently contribute to the score. Report them, but do not let them dominate the summary for a non-commerce product.

## 10. Split frontend and backend repos can overstate readiness

If the authoritative production URL is a public web app but the repository also contains a separate API app, backend OpenAPI or MCP packages are not enough for a pass. Count them as source evidence only until the public runtime exposes or links the discovery surface.

## 11. Keep absolute workstation paths out of the report

Use repo-relative paths such as `apps/web/app/robots.ts` in the markdown report. Reserve absolute local paths for machine-local metadata only when they are genuinely necessary.
