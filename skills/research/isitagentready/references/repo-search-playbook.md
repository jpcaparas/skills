# Repo Search Playbook

Use this playbook to inspect the repository surgically instead of guessing.

## First Pass Search

Start with a broad ripgrep sweep:

```bash
rg -n "robots\\.txt|sitemap|llms\\.txt|llms-full\\.txt|Content-Signal|text/markdown|agent-skills|server-card|agent-card|oauth-protected-resource|openid-configuration|oauth-authorization-server|navigator\\.modelContext|registerTool|x402|\\.well-known|Link:" .
```

Then narrow down by category.

## Static and Generated Files

Check these places first:

- `public/`
- `static/`
- `dist/`
- framework build folders
- docs output folders
- any `.well-known/` directories

Typical files and paths:

- `robots.txt`
- `sitemap.xml`
- `llms.txt`
- `llms-full.txt`
- `.well-known/api-catalog`
- `.well-known/openid-configuration`
- `.well-known/oauth-authorization-server`
- `.well-known/oauth-protected-resource`
- `.well-known/mcp/server-card.json`
- `.well-known/mcp.json`
- `.well-known/agent-card.json`
- `.well-known/agent-skills/index.json`
- `.well-known/ucp`
- `.well-known/acp.json`

## Headers and Content Negotiation

Look for response-header code in:

- Express, Fastify, Hono, Koa, or Nest middleware
- Next.js route handlers or middleware
- Remix loaders and resource routes
- Rails controllers or Rack middleware
- Laravel middleware
- NGINX, Apache, Caddy, or reverse-proxy config
- Vercel, Netlify, or Cloudflare Workers config

Search terms:

```bash
rg -n "text/markdown|Content-Type|setHeader|appendHeader|headers\\(|Link:|service-desc|service-doc|api-catalog|describedby" .
```

## `robots.txt`, AI Rules, and Content Signals

Search terms:

```bash
rg -n "GPTBot|OAI-SearchBot|Claude-Web|Google-Extended|Amazonbot|anthropic-ai|Bytespider|CCBot|Applebot-Extended|Content-Signal|robots.txt" .
```

Evidence to look for:

- explicit named AI crawler blocks
- `Content-Signal:` directives
- generators that render robots content dynamically

## OAuth and Protected Resource Metadata

Search terms:

```bash
rg -n "openid-configuration|oauth-authorization-server|oauth-protected-resource|jwks_uri|authorization_endpoint|token_endpoint|WWW-Authenticate" .
```

Evidence to look for:

- OIDC issuer config
- auth server routes
- resource metadata JSON
- protected API middleware that emits `WWW-Authenticate`

## MCP, A2A, Agent Skills, and WebMCP

Search terms:

```bash
rg -n "mcp|server-card|agent-card|agent-skills|scan_site|navigator\\.modelContext|registerTool|inputSchema|streamable-http" .
```

Evidence to look for:

- JSON documents under `.well-known/`
- MCP server bootstrap code
- Agent Skills indexes and published `SKILL.md` artifacts
- client-side `navigator.modelContext.registerTool()` calls

## API Catalog

Search terms:

```bash
rg -n "api-catalog|application/linkset\\+json|service-desc|service-doc|linkset" .
```

Look for a proper linkset document, not a generic JSON list.

## Commerce Signals

Search terms:

```bash
rg -n "x402|402 Payment Required|@x402/|\\.well-known/ucp|\\.well-known/acp|agentic commerce|facilitator|wallet" .
```

Only pursue these deeply when the product is clearly commerce-capable.

## Deployment and Edge Config

Do not stop at application code. Check:

- `wrangler.toml`
- `vercel.json`
- `netlify.toml`
- `nginx.conf`
- `Dockerfile`
- infra-as-code and CDN rule config

Many agent-readiness signals are implemented there rather than inside the app framework.

## Code-Only Decision Rules

When runtime evidence is unavailable:

- mark `pass` only when the implementation is explicit and low-ambiguity
- mark `partial` when the intended behavior exists but deployment or route exposure is unclear
- mark `unknown` when the search hit is suggestive but incomplete
- mark `not applicable` only with a clear product-scope rationale

## Coverage Checklist

Record the paths you actually inspected:

- public/static assets
- route handlers
- middleware
- edge/CDN config
- auth config
- client scripts
- payment or commerce routes

Include that coverage map in the final report. It is part of the skill contract, not optional.
