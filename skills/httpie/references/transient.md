# Transient HTTPie Workflows

Use this file when you need copy-pasteable shell patterns that leave no HTTPie config, session, or metadata behind.

## Core Disposable Wrapper

Use a subshell so the temp dir, trap, and environment do not leak into the caller:

```bash
(
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin --check-status --body GET https://api.example.com/health
)
```

This is the baseline pattern for one-off HTTPie commands.

## Reusable Shell Helper

```bash
stateless_httpie() (
  set -eu
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin "$@"
)
```

Examples:

```bash
stateless_httpie --check-status --body GET https://api.example.com/health
stateless_httpie --offline POST https://api.example.com/items name=JP active:=true
stateless_httpie --all --follow GET https://example.com
```

## Temporary Session Reuse

When you need a short-lived multi-request flow, keep the session file under the same temp dir:

```bash
(
  tmpdir="$(mktemp -d)"
  session_file="$tmpdir/session.json"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"

  http --ignore-stdin --check-status \
    --session="$session_file" \
    -a demo:password \
    GET https://httpbin.org/basic-auth/demo/password >/dev/null

  http --ignore-stdin --check-status --body \
    --session-read-only="$session_file" \
    GET https://httpbin.org/headers
)
```

That keeps the convenience of HTTPie sessions without teaching the shell to maintain a long-lived cookie jar.

## Read-Only `httpie cli` Usage

Even read-only CLI helpers should stay transient:

```bash
(
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  httpie cli export-args | jq '.spec.name'
)
```

## When `curl` Fallback Is Acceptable

Use a `curl` fallback only when the behavior maps cleanly:

- Plain GETs
- Bearer-token GETs
- Raw JSON bodies from a file
- File downloads

Do not fake a generic fallback for arbitrary HTTPie request-item syntax. If the user asked for HTTPie's expressive request-item language, require HTTPie instead of silently degrading to an incorrect `curl` call.
