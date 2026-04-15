# HTTPie Commands

Use this file when you need the concrete HTTPie command shape, request-item syntax, or a fast translation from `curl`.

All commands in this file assume you run them inside the disposable wrapper from `references/transient.md` unless you have already isolated `HTTPIE_CONFIG_DIR` some other way.

## Why These Commands Beat `curl`

- Request items are shorter and easier to edit than long `-H`, `-d`, and `-F` chains.
- JSON is the default body format, including non-string values.
- Output control is built in: headers, body, metadata, verbose, redirect chains, and streams.
- Offline mode lets you preview a request before it leaves the machine.

## Quick Start

```bash
http --ignore-stdin --check-status --body GET https://api.example.com/health
https --ignore-stdin example.com/health
http --ignore-stdin POST https://api.example.com/items name=JP active:=true
http --ignore-stdin --form POST https://api.example.com/login username=jp password=secret
```

`http` defaults the scheme to `http://`. `https` defaults the scheme to `https://`. Both commands share the same options.

## Request Items

| Syntax | Meaning | Example |
| --- | --- | --- |
| `Header:value` | HTTP header | `Authorization:Bearer-token` |
| `name==value` | Query parameter | `page==2` |
| `name=value` | JSON string field by default | `name=JP` |
| `name:=value` | Non-string JSON field | `active:=true` |
| `field@path` | Form file upload | `avatar@./avatar.png` |
| `field=@path` | Embed file contents as a string field | `note=@./message.txt` |
| `field:=@path` | Embed file contents as raw JSON | `payload:=@./payload.json` |
| `@path` | Raw request body from a file | `@./payload.json` |

Key consequence: `name=value` does not mean form data unless `--form` is present.

## Common Commands

### GET and Query Parameters

```bash
http --ignore-stdin --check-status --body GET https://api.example.com/items page==2 q==widget
http --ignore-stdin GET https://api.example.com/items page==2
```

### JSON Bodies

```bash
http --ignore-stdin --check-status POST https://api.example.com/items \
  name=JP \
  active:=true \
  tags:='["dev", "api"]'
```

### Raw JSON from a File

```bash
http --ignore-stdin --check-status POST https://api.example.com/items \
  Content-Type:application/json \
  @./payload.json
```

Use this when the entire request body already exists as JSON on disk.

### Form Bodies and Uploads

```bash
http --ignore-stdin --check-status --form POST https://api.example.com/login \
  username=jp \
  password=secret

http --ignore-stdin --check-status --form POST https://api.example.com/upload \
  title='Quarterly report' \
  report@./report.pdf
```

### Auth

```bash
http --ignore-stdin --check-status -a user:pass GET https://api.example.com/me
http --ignore-stdin --check-status -A bearer -a "$TOKEN" GET https://api.example.com/me
```

### Output Control

| Need | Command |
| --- | --- |
| Body only | `http --ignore-stdin --body GET https://api.example.com/items` |
| Headers only | `http --ignore-stdin --headers GET https://api.example.com/items` |
| Metadata only | `http --ignore-stdin --meta GET https://api.example.com/items` |
| Full request and response | `http --ignore-stdin -v GET https://api.example.com/items` |
| Fine-grained output | `http --ignore-stdin --print=HBhb GET https://api.example.com/items` |

### Redirect Inspection

```bash
http --ignore-stdin --all --follow GET https://example.com
```

Use this when you need to see the intermediate redirects as well as the final response.

### Streamed Responses

```bash
http --ignore-stdin --stream GET https://api.example.com/events
```

Use this for long-lived responses such as server-sent events or log-style feeds.

### Downloads

```bash
http --ignore-stdin --check-status --download GET https://example.com/archive.zip
http --ignore-stdin --check-status --download --output archive.zip GET https://example.com/archive.zip
http --ignore-stdin --check-status --download --continue --output archive.zip GET https://example.com/archive.zip
```

### Offline Preview

```bash
http --ignore-stdin --offline POST https://api.example.com/items name=JP active:=true
```

Use offline mode when you want to verify the exact request shape before sending it.

## `curl` to HTTPie Translation

Translate the meaning, not the individual flags.

| Intent | `curl` shape | HTTPie shape |
| --- | --- | --- |
| Simple GET | `curl https://api.example.com/items` | `http --ignore-stdin GET https://api.example.com/items` |
| Header | `curl -H 'X-Token: abc' ...` | `http --ignore-stdin ... X-Token:abc` |
| Query string | `curl '...?...=...'` or `-G --data-urlencode` | `http --ignore-stdin GET ... q==value` |
| JSON body | `curl -H 'Content-Type: application/json' -d '{...}'` | `http --ignore-stdin POST ... key=value enabled:=true` |
| JSON body from file | `curl -H 'Content-Type: application/json' --data @payload.json` | `http --ignore-stdin POST ... Content-Type:application/json @payload.json` |
| Form body | `curl -d 'a=b&c=d'` | `http --ignore-stdin --form POST ... a=b c=d` |
| Multipart upload | `curl -F file=@report.pdf` | `http --ignore-stdin --form POST ... file@report.pdf` |
| Basic auth | `curl -u user:pass` | `http --ignore-stdin -a user:pass` |
| Bearer token | `curl -H 'Authorization: Bearer ...'` | `http --ignore-stdin -A bearer -a "$TOKEN"` |
| Follow redirects | `curl -L` | `http --ignore-stdin --follow` |
| Inspect redirect chain | `curl -L -i -v` | `http --ignore-stdin --all --follow -v` |
| Fail on 4xx or 5xx | `curl --fail` | `http --ignore-stdin --check-status` |
| Save to file | `curl -o out.bin URL` | `http --ignore-stdin --download --output out.bin GET URL` |
| Preview without sending | No direct equivalent | `http --ignore-stdin --offline ...` |

## Special Flag Mismatch

Do not map `curl -I` to `http -I`.

- `curl -I` usually means a HEAD request or header-only response inspection.
- `http -I` means `--ignore-stdin`.

Use one of these instead:

```bash
http --ignore-stdin --headers GET https://api.example.com/items
http --ignore-stdin HEAD https://api.example.com/items
http --ignore-stdin --headers HEAD https://api.example.com/items
```

## Exit Codes

By default, HTTPie exits with `0` unless a network or fatal error occurs. Add `--check-status` when 3xx, 4xx, and 5xx responses should produce non-zero exit codes.

Read `references/gotchas.md` when the command looks right but the behavior is surprising.
