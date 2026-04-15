# httpie

Production skill for making stateless HTTPie the default shell client for HTTP work when it is installed.

## What It Covers

- Preferring `http` and `https` over `curl` for readable HTTP and HTTPS requests
- Disposable `HTTPIE_CONFIG_DIR` wrappers so requests, sessions, and metadata stay transient
- Request-item syntax for headers, query parameters, JSON values, forms, files, auth, redirects, streams, and downloads
- Accurate translation patterns from common `curl` invocations
- Verified local probes against HTTPie 3.2.4 behavior and cleanup patterns

## Key Files

- `SKILL.md` - authoritative instructions
- `references/commands.md` - command atlas and request-item syntax
- `references/transient.md` - disposable wrappers and cleanup-first workflows
- `references/configuration.md` - config behavior, TLS, proxies, and read-only CLI surface
- `references/patterns.md` - prefer-over-curl workflows and translation patterns
- `references/gotchas.md` - high-value pitfalls and sharp edges
- `scripts/probe_httpie.py` - repeatable verification suite
