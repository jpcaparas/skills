# HTTPie Configuration

Use this file when you need installation checks, config-directory behavior, TLS settings, proxies, or the read-only `httpie cli` management surface.

## Transient-First Rule

This skill does not rely on the user's ambient HTTPie config directory.

Even read-only HTTPie usage can create files such as `version_info.json`, and session usage obviously writes session files. For this skill, isolate all HTTPie activity in a disposable config dir and delete it on exit.

Read `references/transient.md` first when you need the exact shell wrapper.

## Availability Check

Prefer HTTPie only when it is installed:

```bash
command -v http >/dev/null 2>&1
command -v https >/dev/null 2>&1
http --version
```

If `http` is unavailable, fall back to `curl` or tell the user HTTPie is missing.

## Install and Upgrade

Verified doc paths and local commands reflect HTTPie 3.2.4.

```bash
brew install httpie
brew upgrade httpie
python -m pip install httpie
python -m pip install --upgrade httpie
```

## Disposable Config Directory

Use a temp dir rather than a long-lived config root:

```bash
(
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin --check-status --body GET https://pie.dev/get
)
```

Session files and metadata will live under that temp dir and vanish when the wrapper exits.

## Transient Session Files

When you need short-lived auth or cookies across multiple requests, keep the session file under the same temp dir:

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

Use `--session=SESSION_NAME_OR_PATH` and `--session-read-only=SESSION_NAME_OR_PATH` with explicit file paths to keep the session lifecycle under your control.

## Ephemeral Config File Example

If you need to test HTTPie config options, write the config inside the temp dir, not under a persistent home directory:

```bash
(
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  cat >"$tmpdir/config.json" <<'JSON'
{
  "default_options": [
    "--check-status"
  ]
}
JSON
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin --body GET https://pie.dev/get
)
```

Do not make persistent config files a default recommendation of this skill.

## Proxies

Per-command:

```bash
http --ignore-stdin \
  --proxy=http:http://proxy.internal:3128 \
  --proxy=https:http://proxy.internal:3128 \
  GET https://api.example.com/me
```

Environment variables:

```bash
export HTTP_PROXY=http://10.10.1.10:3128
export HTTPS_PROXY=https://10.10.1.10:1080
export NO_PROXY=localhost,example.com
```

If you export proxy variables in a shell snippet, keep them inside a subshell so they remain transient too.

## TLS and Certificates

```bash
http --ignore-stdin --verify=no GET https://staging.example.internal
http --ignore-stdin --verify=/path/to/ca-bundle.pem GET https://api.example.com
http --ignore-stdin --cert=client.pem --cert-key=client.key GET https://mtls.example.com
```

Use `--verify=no` only for controlled debugging. Prefer a real CA bundle for anything repeatable.

## Read-Only `httpie cli` Surface

The local 3.2.4 install exposes:

```bash
httpie cli --help
httpie cli export-args
httpie cli check-updates
httpie cli sessions --help
httpie cli plugins --help
httpie cli plugins list
```

Keep those subcommands inside a disposable config dir too.

Key points:

- `httpie cli export-args` exposes the parser spec for outside tooling and is safe to use transiently.
- `httpie cli plugins list` is read-only and can be useful for inspection.
- Plugin installation, upgrade, or uninstall mutate state and are not default behavior for this skill.

Read `references/gotchas.md` before you rely on plugin-manager behavior across packaging methods.
