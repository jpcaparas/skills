# HTTPie Gotchas

Use this file when the command looks reasonable but the output, exit code, or behavior does not match expectations.

## 1. Ambient HTTPie config is not stateless enough

Symptom:

- A supposedly read-only HTTPie command still leaves files behind.

Cause:

- HTTPie can write metadata such as `version_info.json`, and sessions obviously create files too.

Fix:

```bash
(
  tmpdir="$(mktemp -d)"
  trap 'rm -rf "$tmpdir"' EXIT HUP INT TERM
  export HTTPIE_CONFIG_DIR="$tmpdir"
  http --ignore-stdin ...
)
```

Treat disposable config dirs as the default, not an optional extra.

## 2. Mixed stdin and request items

Symptom:

- `http key=value ...` errors even though the request items look valid.

Cause:

- In non-interactive environments, HTTPie may still try to read stdin as the raw request body.

Fix:

```bash
http --ignore-stdin ...
```

Keep stdin enabled only when you intentionally pipe the body into HTTPie.

## 3. `curl -I` does not mean `http -I`

Symptom:

- A translated command silently changes meaning or fails oddly.

Cause:

- In HTTPie, `-I` means `--ignore-stdin`, not HEAD or header-only output.

Fix:

```bash
http --ignore-stdin --headers GET https://api.example.com/items
http --ignore-stdin HEAD https://api.example.com/items
```

## 4. `name=value` is JSON, not form data

Symptom:

- The server rejects the request or treats the body as JSON when you expected form fields.

Cause:

- JSON is HTTPie's default body mode.

Fix:

```bash
http --ignore-stdin --form POST https://api.example.com/login username=jp password=secret
```

## 5. Method inference changes with body data

Symptom:

- The command used POST when you expected GET.

Cause:

- HTTPie uses GET when there is no request data and POST when there is.

Fix:

- Spell the method explicitly in examples and automation:

```bash
http --ignore-stdin GET https://api.example.com/items page==2
http --ignore-stdin POST https://api.example.com/items name=JP
```

## 6. `--check-status` changes exit code handling

Symptom:

- A command that used to exit `0` now fails in CI.

Cause:

- `--check-status` maps redirects, client errors, and server errors to non-zero exit codes.

Fix:

- Keep `--check-status` in scripts that should fail fast.
- Omit it for exploratory work where you want to inspect the body regardless of status.

## 7. Session reuse should still be transient

Symptom:

- A session file lingers under the user's real HTTPie state after the command ends.

Cause:

- Named sessions default to host-scoped storage under the active config dir.

Fix:

- Put the session file under a temp dir and clean that temp dir on exit.
- Prefer `--session="$tmpdir/session.json"` and `--session-read-only="$tmpdir/session.json"` over a long-lived named session.

## 8. `https` is a shortcut, not a different TLS engine

Symptom:

- Someone expects `https` to change certificate handling or protocol support.

Cause:

- `https` only changes the default URL scheme to `https://`.

Fix:

- Use the same TLS flags you would use with `http`, such as `--verify`, `--cert`, and `--cert-key`.

## 9. Plugin-manager scope is narrower than it looks

Symptom:

- `httpie cli plugins uninstall` does not remove a plugin you know is installed.

Cause:

- The command manages plugins installed through HTTPie's plugin manager, not every package installed by pip, brew, or system package managers.

Fix:

- Inspect how the plugin was installed before assuming the plugin manager can remove it.
- Prefer read-only plugin inspection in this skill; do not make plugin installation a default recommendation.
