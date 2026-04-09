---
name: markdown-new
description: "Use markdown.new when the user explicitly wants markdown.new, Cloudflare Markdown for Agents, URL-to-Markdown conversion, file-to-Markdown conversion, crawl-to-Markdown, or the hosted markdown.new editor. Trigger on: 'markdown.new', 'convert this URL to markdown', 'crawl this docs site into markdown', 'file to markdown', 'upload this PDF to markdown', 'markdown.new API', or 'markdown editor'. Do NOT trigger for generic web search/scraping when another tool is enough, or for editing local Markdown without using the markdown.new service."
compatibility: "Requires: public URLs reachable by markdown.new; optional curl for API examples"
---

# markdown.new

Use markdown.new to turn public URLs or files into Markdown, crawl a site section into one Markdown document, or use the hosted editor utilities.

Verified against the live service on April 9, 2026 with direct `curl` requests, browser automation, and failure-case probes.

## Decision Tree

What are you trying to do?

- Convert one public page or API response into Markdown
  - Read `references/url-conversion.md`

- Convert a remote file URL or upload a local file
  - Read `references/file-conversion.md`

- Crawl multiple same-site pages and fetch one combined Markdown result
  - Read `references/crawl.md`

- Use the hosted UI pages or the live editor
  - Read `references/editor.md`

- Debug odd behavior, rate limits, query-string edge cases, or bad responses
  - Read `references/gotchas.md`

## Quick Reference

| Task | Command or Route | Read |
| --- | --- | --- |
| Convert one page to Markdown | `curl -s 'https://markdown.new/https://example.com'` | `references/url-conversion.md` |
| Convert one page to JSON | `curl -s 'https://markdown.new/https://example.com?format=json'` | `references/url-conversion.md` |
| Force browser rendering | `curl -s -X POST 'https://markdown.new/' -H 'Content-Type: application/json' -d '{"url":"https://example.com","method":"browser"}'` | `references/url-conversion.md` |
| Convert a remote file URL | `curl -s 'https://markdown.new/https://raw.githubusercontent.com/github/gitignore/main/README.md?format=json'` | `references/file-conversion.md` |
| Upload a local file | `curl -s -X POST 'https://markdown.new/convert' -F 'file=@notes.pdf'` | `references/file-conversion.md` |
| Start a crawl job | `curl -s -X POST 'https://markdown.new/crawl' -H 'Content-Type: application/json' -d '{"url":"https://docs.example.com","limit":50}'` | `references/crawl.md` |
| Poll crawl status as JSON | `curl -s 'https://markdown.new/crawl/status/<jobId>?format=json'` | `references/crawl.md` |
| Open the hosted editor | `https://markdown.new/markdown-editor` | `references/editor.md` |

## Reading Guide

| If the user says... | Read |
| --- | --- |
| "Use markdown.new on this URL" | `references/url-conversion.md` |
| "Turn this PDF / CSV / raw file URL into Markdown" | `references/file-conversion.md` |
| "Crawl this docs section into one Markdown export" | `references/crawl.md` |
| "What does the markdown.new UI/editor support?" | `references/editor.md` |
| "Why did markdown.new return junk / 500 / no tokens?" | `references/gotchas.md` |

## Verified Behaviors

1. Bare domains are normalized. `https://markdown.new/example.com?format=json` resolved to `https://example.com` in testing.
2. `GET /<url>` defaults to `text/markdown`, while `GET /<url>?format=json` and `POST /` return JSON.
3. `retain_images=true` changes output. Browser-mode conversion of `https://www.python.org/` produced Markdown image syntax only when `retain_images` was true.
4. GitHub raw file URLs work well. GitHub `blob` URLs returned HTML-heavy noise in testing.
5. Crawl jobs are cached. Re-running a crawl on `https://example.com` returned a cached job created on April 3, 2026.

## Gotchas

1. **Use POST for complex target URLs**: URLs with their own query strings were reliable with `POST /` but a fully percent-encoded GET path returned HTTP 400 in testing.
2. **Do not trust `method` as provenance**: the service documents a native Markdown-first pipeline, but a known Markdown endpoint still reported `Cloudflare Workers AI` in a live test.
3. **Expect weak error reporting**: missing `url`, malformed JSON, bogus crawl IDs, and invalid paths returned 400/500 without a useful error body in testing.
4. **Do not assume `tokens` always exists**: browser-mode responses omitted `tokens` in testing even when the conversion succeeded.
5. **Crawl limits are documented inconsistently**: the homepage says 100 pages in one section, while the crawl page says 500 pages and accepts `limit` values up to 500.

## Helper Script

Use `scripts/probe_markdown_new.py` when you want a structured probe instead of hand-writing `curl` commands. It wraps the main GET, POST, crawl, status, and upload flows and prints JSON with the HTTP status, selected headers, and parsed body.
