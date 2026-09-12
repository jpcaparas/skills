# URL Conversion

Use this reference when the user wants markdown.new to convert one public URL into Markdown.

## When to use this path

- A public web page should become clean Markdown.
- The user wants markdown.new specifically, not just "scrape this page somehow."
- The target URL is easier to fetch than to browse interactively.

Do not use this path for local file uploads. Use `references/file-conversion.md` for that.

## Verified endpoints

| Flow | Request | Verified on April 9, 2026 | Notes |
| --- | --- | --- | --- |
| Plain Markdown response | `GET https://markdown.new/https://example.com` | Yes | Returns `text/markdown; charset=utf-8` |
| JSON response | `GET https://markdown.new/https://example.com?format=json` | Yes | Returns JSON with `success`, `url`, `title`, `content`, `timestamp`, `method`, `duration_ms`, `tokens` |
| JSON body API | `POST https://markdown.new/` with `{"url":"https://example.com"}` | Yes | Returns JSON immediately |
| Force browser rendering | `POST https://markdown.new/` with `{"url":"https://example.com","method":"browser"}` | Yes | Returned `method: Cloudflare Browser Rendering` |
| Retain images | `POST https://markdown.new/` with `{"url":"https://www.python.org/","method":"browser","retain_images":true}` | Yes | Produced Markdown image syntax in output |

## Request shapes

### GET path-prefix mode

Use this for simple URLs that do not need extra body parameters.

```bash
curl -s 'https://markdown.new/https://example.com'
curl -s 'https://markdown.new/https://example.com?format=json'
```

Observed headers for the Markdown response included:

- `content-type: text/markdown; charset=utf-8`
- `x-markdown-tokens: 42`
- `cache-control: public, max-age=300`

### POST JSON mode

Use this when you need options or when the target URL has its own query string.

```bash
curl -s -X POST 'https://markdown.new/' \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'

curl -s -X POST 'https://markdown.new/' \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com","method":"browser","retain_images":true}'
```

Observed JSON shape:

```json
{
  "success": true,
  "url": "https://example.com",
  "title": "Example Domain",
  "content": "# Example Domain\n\n...",
  "timestamp": "2026-04-09T08:28:58.833Z",
  "method": "Cloudflare Workers AI",
  "duration_ms": 555,
  "tokens": 42
}
```

Browser-mode responses were successful but did not always include `tokens`.

## Parameters

### `method`

Documented values:

- `auto`
- `ai`
- `browser`

Verified behavior:

- `browser` forced the browser path and returned `method: Cloudflare Browser Rendering`.
- An invalid value such as `bogus` did not error in testing. The request still succeeded and fell back to `Cloudflare Workers AI`.

Treat invalid values as unsafe. Validate client-side if you care which pipeline ran.

### `retain_images`

Documented as a boolean supported in query params or POST body.

Verified behavior:

- `retain_images: true` in POST body changed the output for `https://www.python.org/`.
- `retain_images: false` produced no Markdown image syntax for the same page.

If images matter, prefer POST JSON so the option is unambiguous.

### `format=json`

Verified on GET:

```bash
curl -s 'https://markdown.new/https://example.com?format=json'
```

This is the easiest way to keep a pure GET flow while receiving structured output.

## Source-type matrix

| Source type | Works well? | What happened in testing |
| --- | --- | --- |
| Public HTML page | Yes | `https://example.com` converted cleanly |
| Public docs page from search | Yes | `https://docs.python.org/3/tutorial/index.html` and MDN's Fetch API page both converted cleanly |
| Large reference page from search | Mixed | `https://react.dev/reference/react/useEffect` converted, but produced a very large response |
| Very large encyclopedia page from search | Mixed | `https://en.wikipedia.org/wiki/Alan_Turing` converted successfully but produced a massive response |
| Bare domain with no scheme | Yes | `example.com` normalized to `https://example.com` |
| Raw Markdown file URL | Yes | `raw.githubusercontent.com/.../README.md` returned clean Markdown |
| Raw CSV file URL | Yes | Returned fenced CSV Markdown |
| GitHub `blob` page URL | No | Returned HTML-heavy junk, not the file contents |
| URL with its own query string via POST | Yes | `https://httpbin.org/anything?foo=bar&baz=qux` worked via `POST /` |
| Fully percent-encoded target URL in GET path | No | Returned HTTP 400 in testing |

## Query-string and encoding rules

Use these rules to avoid brittle requests:

1. Prefer `POST /` for target URLs with their own query strings.
2. Use GET path-prefix mode only for simple targets such as `https://example.com/path`.
3. Do not assume that percent-encoding the entire target URL makes GET mode safe. A full encoded path returned HTTP 400 in testing.
4. Ignore fragment identifiers for fetching. `#section` is a client-side hint and is not sent to the server as part of an HTTP request.

### Recommended pattern for query-string targets

```bash
curl -s -X POST 'https://markdown.new/' \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://httpbin.org/anything?foo=bar&baz=qux"}'
```

This preserved the inner query parameters in a live test.

## Observed upstream request details

Using `https://httpbin.org/anything` as a probe showed that markdown.new sent:

- `User-Agent: markdown.new/1.0`
- `Accept: text/markdown, text/html;q=0.9`

That aligns with the product claim that it asks for Markdown first.

## Reliability notes

- The documented native Markdown-first pipeline is plausible, but a known Markdown endpoint still reported `Cloudflare Workers AI` in testing. Treat `method` as advisory metadata, not a source-of-truth audit trail.
- `x-rate-limit-remaining` is documented on the homepage FAQ, but it was not present in the headers observed during successful conversion tests.
- Large public pages can be technically successful but still operationally awkward. The React `useEffect` page returned about 14k tokens, and the Alan Turing Wikipedia page returned about 74k tokens in testing.

## Helper script

Use `scripts/probe_markdown_new.py` for repeatable probes:

```bash
python3 scripts/probe_markdown_new.py --mode get 'https://example.com' --json-response
python3 scripts/probe_markdown_new.py --mode post 'https://httpbin.org/anything?foo=bar&baz=qux'
python3 scripts/probe_markdown_new.py --mode post 'https://www.python.org/' --force-method browser --retain-images
```

See also `references/gotchas.md` for failure patterns and `references/file-conversion.md` when the source is a file instead of a page.
