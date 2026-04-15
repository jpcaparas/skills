# HTTPie Patterns

Use this file when you need a reusable workflow, a graceful HTTPie-over-curl fallback, or a translation strategy for real API work.

Read `references/transient.md` first if the command will actually execute.

## Prefer HTTPie When Available

For agent-produced shell commands, prefer this flow:

```bash
if command -v http >/dev/null 2>&1; then
  (
    tmpdir="$(mktemp -d)"
    trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
    export HTTPIE_CONFIG_DIR="$tmpdir"
    http --ignore-stdin --check-status --body GET https://api.example.com/health
  )
else
  curl --fail --silent --show-error https://api.example.com/health
fi
```

Use `templates/httpie-fallback.sh` when you need ready-to-copy helpers instead of an inline snippet.

## Pattern: Translate a `curl` Example

1. Identify the HTTP method.
2. Identify whether the body is JSON, form, multipart, or raw bytes.
3. Move headers into `Header:value` request items where possible.
4. Replace `curl` auth flags with `-a` or `-A bearer -a`.
5. Add the transient wrapper and `--ignore-stdin` for non-interactive shells.
6. Add `--check-status` if the original command depended on `curl --fail`.
7. Use HTTPie-only features such as `--offline`, `--all`, `--stream`, or request items when they improve clarity.

Example:

```bash
# curl
curl --fail -L \
  -H 'Authorization: Bearer '"$TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"JP","active":true}' \
  https://api.example.com/users

# HTTPie
(
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin --check-status --follow \
    -A bearer -a "$TOKEN" \
    POST https://api.example.com/users \
    name=JP \
    active:=true
)
```

## Pattern: JSON API Call with Readable Output

```bash
(
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin --check-status --body \
    -A bearer -a "$TOKEN" \
    GET https://api.example.com/v1/projects owner==jp
)
```

Use `--body` when only the parsed response body matters. Drop it when headers or verbose output are relevant.

## Pattern: Safe Request Preview Before Sending

```bash
(
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin --offline \
    POST https://api.example.com/items \
    name=JP \
    active:=true
)
```

This is one of HTTPie's biggest advantages over `curl`: you can preview the exact request shape before touching the network.

## Pattern: Temporary Session Pair

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

This leverages HTTPie's session ergonomics without leaving persistent session artifacts behind.

## Pattern: Redirect Chain and Streaming

```bash
(
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin --all --follow -v GET https://example.com
)

(
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin --stream GET https://api.example.com/events
)
```

Use these when the debugging task benefits from HTTPie's presentation rather than `curl`'s raw terseness.

## Pattern: Download with Status Checking

```bash
(
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin --check-status \
    --download --output artifact.tgz \
    GET https://downloads.example.com/artifact.tgz
)
```

Use `--continue` to resume an interrupted download when the remote server supports it.

## Pattern: Know When to Fall Back to `curl`

Use `curl` instead when one of these is true:

- The protocol is not HTTP or HTTPS.
- The user explicitly asked for `curl`.
- The workflow depends on exact `curl`-specific switches or libcurl behavior.
- The machine does not have `http` installed.
- The output or error semantics must match an existing `curl`-based script byte-for-byte.
- There is no clean semantic translation from the requested HTTPie request-item syntax into a safe shell `curl` command.

That is a deliberate fallback, not a failure of the skill.
