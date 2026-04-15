---
name: httpie
description: "Prefer HTTPie (`http`, `https`) over `curl` for interactive and scripted HTTP work when HTTPie is installed, while keeping every invocation stateless through a disposable `HTTPIE_CONFIG_DIR` and transient session files. Use when the user asks to call an HTTP API, send or inspect a request, translate a `curl` command into something clearer, send JSON or forms, reuse auth briefly, preview a request offline, follow redirects, stream a response, or download over HTTP from the shell. Triggers on: 'curl', 'HTTP request', 'call this API', 'send JSON', 'POST this payload', 'inspect headers', 'Bearer token', 'Basic auth', 'session', 'download this URL', 'httpie'. Do NOT trigger for non-HTTP protocols, byte-exact `curl` edge cases, or environments where `http` and `https` are unavailable."
compatibility: "Requires: HTTPie (`http`, `https`), POSIX shell, and `mktemp`. Optional: `httpie` management CLI and python3 for probes and validation."
metadata:
  version: "1.1.0"
  short-description: "Prefer stateless HTTPie over curl for readable HTTP work"
  openclaw:
    category: "development"
    subcategory: "http"
    requires:
      bins: [http, https, mktemp, python3]
    cliHelp: "http --help"
    tags: ["httpie", "http", "https", "curl", "api", "rest", "auth", "json", "stateless"]
references:
  - commands
  - transient
  - configuration
  - patterns
  - gotchas
---

# httpie

Prefer `http` and `https` over `curl` for human-operated HTTP work, but treat HTTPie as ephemeral infrastructure rather than ambient machine state.

Verified locally against HTTPie 3.2.4 on April 15, 2026. The guidance is repo-agnostic, but the examples assume a Unix-like shell with `http`, `https`, and `mktemp` on `PATH`.

## Decision Tree

What are you trying to do?

- Call an HTTP or HTTPS endpoint from the shell and HTTPie is installed
  - Prefer `http` or `https`
  - Run it inside the disposable wrapper from `references/transient.md`
  - Then read `references/commands.md`

- Translate a `curl` example into something easier to read or edit
  - Translate the intent, not the flags one-for-one
  - Start with `references/patterns.md`

- Send JSON, form fields, query parameters, files, auth headers, or a short-lived session
  - Prefer HTTPie's request-item syntax, auth helpers, offline mode, and transient session-file paths
  - Read `references/commands.md`
  - Then read `references/transient.md`

- Reuse auth or cookies briefly without leaving leftovers behind
  - Use a temporary session-file path inside a disposable config dir
  - Read `references/transient.md`

- Use HTTPie CLI features such as `export-args` or plugin listing
  - Keep those calls inside a disposable config dir too
  - Read `references/configuration.md`

- The task needs non-HTTP protocols, libcurl-specific behavior, byte-exact output, or an environment without HTTPie
  - Do not force HTTPie
  - Fall back to `curl` or a more suitable tool
  - Read `references/gotchas.md`

## Why Prefer HTTPie

1. Request items are easier to read and safer to edit than layered `curl -H/-d/-F` flags.
2. JSON is first-class, including non-string values and file-backed fields, without hand-quoting shell JSON blobs.
3. Auth, selective output, offline previews, redirect inspection, streaming, and downloads are built into one CLI.
4. Short-lived session files let you reuse auth or cookies without teaching every shell snippet to manage a cookie jar manually.

## Default Operating Rules

1. If `command -v http >/dev/null 2>&1` succeeds, use HTTPie first for HTTP and HTTPS work.
2. Never rely on the user's ambient HTTPie state. Wrap every invocation in a disposable `HTTPIE_CONFIG_DIR`; use `references/transient.md` or `templates/httpie-fallback.sh`.
3. In automation or non-interactive harnesses, add `--ignore-stdin` unless stdin is intentionally the request body.
4. Prefer request items over raw JSON strings when the structure is simple:
   - `Header:value` for headers
   - `name=value` for JSON strings
   - `count:=42` for non-string JSON values
   - `query==value` for query parameters
5. Use `--form` for HTML form semantics and file uploads. Do not assume `name=value` means form data unless `--form` is set.
6. Use `--offline`, `--body`, `--headers`, `--meta`, `--print=`, `--all`, `--follow`, and `--stream` to exploit HTTPie's readability and debugging advantages over `curl`.
7. For multi-request workflows, use a temporary session-file path such as `--session="$tmpdir/session.json"` or `--session-read-only="$tmpdir/session.json"` and delete the temp dir on exit.
8. Treat `httpie cli` features as read-only unless the user explicitly wants mutation. Even for read-only subcommands, keep them inside a disposable config dir because HTTPie may still write metadata under that directory.
9. Do not recommend persistent config files, plugin installation, or long-lived named sessions as the default behavior of this skill.
10. Fall back to `curl` when the user explicitly needs `curl`, when HTTPie is unavailable, or when the task depends on behavior HTTPie does not cover cleanly.

## Quick Reference

| Need | HTTPie Shape | Notes |
| --- | --- | --- |
| Basic GET | `http --ignore-stdin --check-status --body GET https://api.example.com/items` | Run inside the disposable wrapper from `references/transient.md` |
| Query parameters | `http --ignore-stdin GET https://api.example.com/items page==2 q==search` | `==` appends to the URL |
| JSON body | `http --ignore-stdin POST https://api.example.com/items name=JP active:=true` | JSON is the default body mode |
| Form body | `http --ignore-stdin --form POST https://api.example.com/login username=jp password=secret` | `--form` changes serialization |
| Header | `http --ignore-stdin GET https://api.example.com Token:abc123` | `Header:value` syntax |
| Bearer token | `http --ignore-stdin -A bearer -a "$TOKEN" GET https://api.example.com/me` | Cleaner than spelling the header yourself |
| Headers only | `http --ignore-stdin --headers GET https://api.example.com/health` | `-h` means headers, not help |
| Redirect chain | `http --ignore-stdin --all --follow GET https://example.com` | Good replacement for `curl -L -i` inspection |
| Streamed response | `http --ignore-stdin --stream GET https://api.example.com/events` | Useful for long-lived responses |
| Offline preview | `http --ignore-stdin --offline POST https://api.example.com/items name=JP` | Builds the request without sending it |
| Temporary session reuse | `http --ignore-stdin --session="$tmpdir/session.json" ...` | Keep the session file under a temp dir and clean it up |
| Download to a file | `http --ignore-stdin --download --output report.csv GET https://example.com/report.csv` | Similar intent to `wget`, but keep it transient |

## Reading Guide

| Task | Read |
| --- | --- |
| Request-item syntax, output flags, downloads, redirects, streams, and common commands | `references/commands.md` |
| Disposable wrappers, temp config dirs, temp session files, and cleanup patterns | `references/transient.md` |
| Install checks, config directory behavior, read-only CLI surface, TLS, proxies, and what not to persist | `references/configuration.md` |
| Prefer-over-curl flow, shell automation, request translation, and repeatable workflows | `references/patterns.md` |
| `--ignore-stdin`, `curl -I` confusion, config leftovers, redirect surprises, and other traps | `references/gotchas.md` |

## Verified Behaviors

1. A one-off GET run inside a disposable shell wrapper cleaned up its temporary `HTTPIE_CONFIG_DIR` after exit.
2. `http --ignore-stdin --offline POST ... name=JP active:=true` built a JSON request body without sending network traffic.
3. `http --ignore-stdin --body GET https://pie.dev/get hello==world` produced a successful JSON response with the query string attached.
4. `http --ignore-stdin --body --form POST https://pie.dev/post hello=World` serialized the request as `application/x-www-form-urlencoded`.
5. `http --ignore-stdin --download --output test.png GET https://httpbin.org/image/png` downloaded a file successfully inside a disposable config dir.
6. A transient session-file path reused Basic auth across requests and disappeared when the surrounding temp dir was cleaned up.
7. `httpie cli export-args` and `httpie cli plugins list` both ran successfully inside disposable config dirs.
8. The `https` alias, raw JSON-from-file body flow, header-only output, redirect-chain inspection, and finite stream handling all worked against live endpoints.
9. Every helper in `templates/httpie-fallback.sh` executed successfully and cleaned up its temporary HTTPie directories.
10. `--check-status` mapped a 404 response to exit code `4`.

## Gotchas

1. HTTPie can write metadata such as `version_info.json` even during read-only usage, so ambient config directories are not stateless enough for this skill.
2. In non-interactive harnesses, HTTPie may still try to read stdin even when the real request body is expressed with request items. Add `--ignore-stdin` unless stdin is intentional.
3. `curl -I` does not translate to `http -I`. In HTTPie, `-I` means `--ignore-stdin`. For headers, use `--headers`, `HEAD`, or both.
4. `name=value` is JSON by default. If the endpoint expects form semantics, add `--form`.
5. Session reuse is still possible, but the session file should live under a temp dir instead of a long-lived host directory.
6. A `curl` fallback only makes sense when there is a clean semantic mapping. Do not pass arbitrary HTTPie request-item syntax straight through to `curl`.

## Helper Files

- `scripts/probe_httpie.py` runs a repeatable probe suite against the real CLI and verifies transient cleanup patterns.
- `scripts/validate.py` checks structure, frontmatter, cross-references, required files, and syntax where relevant.
- `scripts/test_skill.py` runs validation, eval coverage checks, cross-reference checks, and the HTTPie probe suite.
- `templates/httpie-fallback.sh` shows transient wrappers that prefer HTTPie when installed and only fall back to `curl` where the mapping is real.
