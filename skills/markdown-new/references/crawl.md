# Crawl

Use this reference when markdown.new should crawl multiple pages from one site section and return one combined Markdown export.

## Verified endpoints

| Flow | Request | Verified on April 9, 2026 | Notes |
| --- | --- | --- | --- |
| Start crawl job | `POST https://markdown.new/crawl` | Yes | Returned cached job metadata for `https://example.com` |
| Poll crawl as JSON | `GET https://markdown.new/crawl/status/<jobId>?format=json` | Yes | Returned structured job result with `records[]` |
| Fetch combined Markdown | `GET https://markdown.new/crawl/status/<jobId>` | Yes | Returned a concatenated Markdown document |
| Browser shortcut | `https://markdown.new/crawl/https://example.com` | Indirectly verified via UI | The UI navigated to `/crawl/status/<jobId>` |
| Cancel crawl | `DELETE https://markdown.new/crawl/status/<jobId>` | Yes | Returned HTTP 500 on a cached completed job |

## Start a crawl

```bash
curl -s -X POST 'https://markdown.new/crawl' \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com","limit":1,"depth":1}'
```

Observed response:

```json
{
  "success": true,
  "jobId": "6fe0760d-e75e-4616-ad9a-ad2d2665af2c",
  "statusUrl": "/crawl/status/6fe0760d-e75e-4616-ad9a-ad2d2665af2c",
  "cached": true,
  "cachedAt": "2026-04-03 17:11:33"
}
```

The repeated request for the same URL also returned the same cached job ID.

## Poll crawl status

### JSON

```bash
curl -s 'https://markdown.new/crawl/status/6fe0760d-e75e-4616-ad9a-ad2d2665af2c?format=json'
```

Observed shape:

```json
{
  "success": true,
  "result": {
    "id": "6fe0760d-e75e-4616-ad9a-ad2d2665af2c",
    "status": "completed",
    "browserSecondsUsed": 0,
    "total": 1,
    "finished": 1,
    "skipped": 0,
    "records": [
      {
        "url": "https://example.com/",
        "status": "completed",
        "metadata": {
          "status": 200,
          "title": "Example Domain",
          "url": "https://example.com/",
          "lastModified": "Tue, 07 Apr 2026 22:07:07 GMT"
        },
        "markdown": "# Example Domain\n\n..."
      }
    ]
  }
}
```

### Default Markdown

```bash
curl -s 'https://markdown.new/crawl/status/6fe0760d-e75e-4616-ad9a-ad2d2665af2c'
```

Observed output:

```markdown
# Crawl Results

Job ID: 6fe0760d-e75e-4616-ad9a-ad2d2665af2c
Pages: 1/1

---

## https://example.com/

# Example Domain
...
```

## Documented options

The crawl page documents these request body fields:

| Field | Meaning | Default |
| --- | --- | --- |
| `url` | Starting URL | required |
| `limit` | Max pages to crawl | `500` |
| `depth` | Max link depth from start URL | `5` |
| `render` | Enable JS rendering for SPAs | `false` |
| `source` | URL discovery source: `all`, `sitemaps`, or `links` | `all` |
| `maxAge` | Max cache age in seconds | `86400` |
| `modifiedSince` | Only crawl pages modified after this Unix timestamp | none |
| `includeExternalLinks` | Follow external domains | `false` |
| `includeSubdomains` | Follow subdomains | `false` |
| `includePatterns` | Only crawl matching wildcard patterns | auto |
| `excludePatterns` | Skip matching wildcard patterns | none |

These options were documented on the site. The `example.com` probe only verified `url`, `limit`, and `depth` directly.

## Cache behavior

The crawl API is cache-aware:

- Starting a crawl can return `cached: true`
- The UI shows `Cached - showing results from ...`
- The same crawl target can return an old job rather than creating a new one immediately

If freshness matters, use the documented `maxAge` field or the UI's `Re-crawl` button.

## Limits and retention

Documented on the crawl page:

- Up to 500 pages per crawl
- Results stored for 14 days
- Each crawl costs 50 request units, which the FAQ translates to roughly 10 crawls per day under a 500-request daily limit

One inconsistency matters:

- The homepage promo block says 100 pages
- The dedicated crawl page says 500 pages

Treat 500 as the documented crawl-page contract, but surface the inconsistency if the user is budgeting around limits.

## Failure behavior

Observed live behavior:

- `GET /crawl/status/not-a-real-job?format=json` returned HTTP 500 with no useful body
- `DELETE /crawl/status/<cached-completed-job>` returned HTTP 500

Do not depend on detailed error payloads from crawl endpoints. Validate obvious bad inputs before you send them.

## Browser UI observations

Browser automation verified that:

- `https://markdown.new/crawl` exposes a URL textbox and `Start Crawl`
- Starting a crawl from the UI navigates to `/crawl/status/<jobId>`
- The status page exposes `Re-crawl`, `Download .md`, `Copy All`, and `New Crawl`

That makes the crawl UI usable for humans, but agents should prefer the HTTP endpoints for deterministic work.

## Helper script

```bash
python3 scripts/probe_markdown_new.py --mode crawl-start 'https://example.com' --limit 1 --depth 1
python3 scripts/probe_markdown_new.py --mode crawl-status '6fe0760d-e75e-4616-ad9a-ad2d2665af2c' --json-response
```

See also `references/gotchas.md` for cache and delete quirks.
