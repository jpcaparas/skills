# Signal Map

This file maps Cloudflare's agent-readiness signals to concrete runtime checks and repository evidence.

Use it together with `references/repo-search-playbook.md`.

## Score Structure

Cloudflare's April 17, 2026 blog groups the score into four dimensions:

- Discoverability
- Content
- Bot Access Control
- Capabilities

Commerce checks are evaluated separately and do not currently count toward the score.

## Discoverability

| Signal | Official key | Runtime expectation | Repository evidence to inspect | Applicability | Score |
| --- | --- | --- | --- | --- | --- |
| `robots.txt` | `checks.discoverability.robotsTxt` | `GET /robots.txt` returns `200` and `text/plain` | `public/robots.txt`, generated route handlers, middleware, CDN-generated plain text | Required for any public site | Yes |
| `sitemap.xml` | `checks.discoverability.sitemap` | `GET /sitemap.xml` or equivalent returns valid XML | `public/sitemap.xml`, generated sitemaps, route code, framework sitemap generators | Required for public content or crawlable apps | Yes |
| Link headers | `checks.discoverability.linkHeaders` | Homepage emits `Link` headers such as `api-catalog`, `service-doc`, `service-desc`, `describedby` | response header config, middleware, reverse proxy config, edge rules | Strongly recommended; most relevant when machine-readable resources exist | Yes |

## Content

| Signal | Official key | Runtime expectation | Repository evidence to inspect | Applicability | Score |
| --- | --- | --- | --- | --- | --- |
| Markdown negotiation | `checks.contentAccessibility.markdownNegotiation` | Requests with `Accept: text/markdown` return markdown plus `Content-Type: text/markdown` | header negotiation, content renderers, markdown serializers, Cloudflare Markdown for Agents config, edge rewrite rules | Required for content sites and useful for most doc-heavy products | Yes |
| `llms.txt` | customized scan / supporting signal | `GET /llms.txt` returns plain text overview with title and key links | `public/llms.txt`, generator scripts, docs build outputs | Supporting signal, not the default scored check | Supporting |
| `llms-full.txt` | customized scan / supporting signal | `GET /llms-full.txt` returns expanded text content | generated text artifact, docs build output, `llms.txt` link to full file | Supporting signal, especially for large docs sites | Supporting |

## Bot Access Control

| Signal | Official key | Runtime expectation | Repository evidence to inspect | Applicability | Score |
| --- | --- | --- | --- | --- | --- |
| AI bot rules in `robots.txt` | `checks.botAccessControl.robotsTxtAiRules` | `robots.txt` includes explicit blocks for named AI crawlers, not only `User-agent: *` | `robots.txt` content, generators, CMS templates | Required when publishing crawl policy for AI bots | Yes |
| Content Signals | `checks.botAccessControl.contentSignals` | `robots.txt` includes `Content-Signal:` directives such as `ai-train`, `search`, `ai-input` | same places as `robots.txt`, AI crawl policy config | Relevant for sites with a deliberate AI usage policy | Yes |
| Web Bot Auth | `checks.botAccessControl.webBotAuth` | `/.well-known/http-message-signatures-directory` exists and bots sign outbound requests | JWKS or key directories, request-signing code, bot clients, edge auth config | Neutral or optional unless the site sends bot or agent requests to other sites | Often neutral |

## Capabilities / Discovery

| Signal | Official key | Runtime expectation | Repository evidence to inspect | Applicability | Score |
| --- | --- | --- | --- | --- | --- |
| API Catalog | `checks.discovery.apiCatalog` | `/.well-known/api-catalog` returns `application/linkset+json` with service links | linkset JSON, generated `.well-known` docs, OpenAPI docs tooling | Relevant when the product exposes one or more public APIs | Yes when applicable |
| OAuth discovery | `checks.discovery.oauthDiscovery` | `/.well-known/openid-configuration` or `/.well-known/oauth-authorization-server` exists | identity provider config, OIDC issuer docs, auth server routes | Relevant for products that expect agent access via OAuth/OIDC | Yes when applicable |
| OAuth Protected Resource Metadata | `checks.discovery.oauthProtectedResource` | `/.well-known/oauth-protected-resource` exists, may also be advertised in `WWW-Authenticate` | resource server metadata, auth middleware, protected API routes | Relevant when APIs are protected resources | Yes when applicable |
| MCP Server Card | `checks.discovery.mcpServerCard` | scanner may probe `/.well-known/mcp/server-cards.json`, `/.well-known/mcp/server-card.json`, and `/.well-known/mcp.json` | MCP server config, `.well-known` JSON, agents SDK setup | Relevant when the product exposes MCP tools or resources | Yes when applicable |
| A2A Agent Card | `checks.discovery.a2aAgentCard` | `/.well-known/agent-card.json` exists with interfaces, capabilities, and skills | agent metadata, `.well-known` JSON, agent gateway config | Relevant when the product exposes agent-to-agent capabilities | Yes when applicable |
| Agent Skills discovery | `checks.discovery.agentSkills` | `/.well-known/agent-skills/index.json` exists; scanner may also probe legacy `/.well-known/skills/index.json` | skill index JSON, published SKILL.md files or archives, digests | Relevant when the site publishes task-specific skills for agents | Yes when applicable |
| WebMCP | `checks.discovery.webMcp` | browser-rendered page registers tools via `navigator.modelContext.registerTool()` | client scripts, hydration entrypoints, browser-only components | Relevant when site actions should be exposed in-browser to agents | Yes when applicable |

## Commerce

| Signal | Official key | Runtime expectation | Repository evidence to inspect | Applicability | Score |
| --- | --- | --- | --- | --- | --- |
| x402 | `checks.commerce.x402` | protected routes return `402 Payment Required` with machine-readable payment details | x402 middleware, route wrappers, wallet/facilitator config | Only for agent-native paid APIs or content | No |
| UCP | `checks.commerce.ucp` | `/.well-known/ucp` exists with services, capabilities, and endpoints | `.well-known/ucp` generator or static file | Only for agentic commerce flows | No |
| ACP | `checks.commerce.acp` | `/.well-known/acp.json` exists with protocol, transports, and services | `.well-known/acp.json` generation, commerce config | Only for agentic commerce flows | No |

## Per-Signal Notes

### `robots.txt`

- Cloudflare's skill requires `200`, `text/plain`, and explicit directives.
- Treat HTML responses, soft 404s, or framework fallthrough routes as failures even if the file name exists in source.

### `sitemap.xml`

- Prefer canonical URLs only.
- Generated framework sitemaps count if the deployed path really resolves.

### Link headers

- Search both app code and infra config.
- The official guidance highlights `api-catalog`, `service-desc`, `service-doc`, and `describedby`.

### Markdown negotiation

- This is the core content accessibility signal in the default score.
- Returning HTML on `Accept: text/markdown` is a runtime fail even if markdown source files exist in the repo.

### `llms.txt` and `llms-full.txt`

- Cloudflare's blog says the default check emphasizes markdown negotiation and that `llms.txt` can be added in customized scans.
- Treat these as high-value supporting signals, especially for docs-heavy repositories.

### AI bot rules

- Explicit named crawler blocks matter. A wildcard-only policy is not enough for the Cloudflare `ai-rules` skill.

### Content Signals

- Look for `Content-Signal:` directives near the relevant `User-agent` blocks.

### Web Bot Auth

- Cloudflare's own scan can return this as informational or neutral for sites that do not send bot requests.
- Do not over-penalize content-only properties for lacking outbound request signing.

### API Catalog

- The expected format is a linkset JSON document, not a random JSON index.

### OAuth discovery and Protected Resource Metadata

- These are easy to over-report. Only expect them when the repo actually exposes protected APIs or delegated agent access.

### MCP Server Card

- Check multiple candidate locations. The live scanner probes more than one path.
- Evidence in repo may live in Workers, edge handlers, or agent gateway code rather than the main app.

### A2A Agent Card and Agent Skills

- These are protocol discovery artifacts. Prefer `.well-known` JSON or published skill artifacts over ad hoc docs pages.

### WebMCP

- This is effectively a browser check. Source matches must still be confirmed in a rendered page when possible.

### Commerce signals

- Cloudflare explicitly says commerce checks are currently non-scoring.
- Treat them as optional enhancements unless the product is clearly commerce-capable.
