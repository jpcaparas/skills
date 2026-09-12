# Editor and UI Pages

Use this reference when the task is about the hosted markdown.new UI rather than the raw HTTP endpoints.

## Surface map

| Route | Purpose | Verified on April 9, 2026 |
| --- | --- | --- |
| `https://markdown.new/` | Landing page for URL-to-Markdown conversion | Yes |
| `https://markdown.new/file-to-markdown` | Browser UI for remote file URLs or uploads | Yes |
| `https://markdown.new/crawl` | Browser UI for multi-page crawl jobs | Yes |
| `https://markdown.new/markdown-editor` | Live Markdown editor with preview and export buttons | Yes |
| `https://markdown.new/terms` | Terms page | Mapped, not deeply analyzed |
| `https://markdown.new/privacy` | Privacy page | Mapped, not deeply analyzed |

## Landing page

The homepage presents:

- A URL textbox
- A `Convert` button
- Documentation snippets for path-prefix and POST usage
- Links to the file converter, crawl page, editor, and Cloudflare blog post

Important automation note:

- In one browser automation session, filling the homepage textbox and clicking `Convert` did not navigate away from `/`.
- The direct HTTP paths and the crawl UI were reliable.

For agent workflows, prefer:

- direct GET path-prefix URLs
- `POST /` JSON requests
- the crawl UI or crawl API

## File-to-Markdown page

Browser automation confirmed these controls:

- `Paste File URL`
- `Upload File`
- a file URL textbox
- `Convert`

Use this page for human-driven uploads when the caller is already in a browser. Use `POST /convert` for deterministic automation.

## Crawl page

Browser automation confirmed:

- one URL textbox
- `Start Crawl`
- navigation to `/crawl/status/<jobId>` after starting a crawl
- status-page actions: `Re-crawl`, `Download .md`, `Copy All`, `New Crawl`

This is the most reliable browser flow on the site from an automation perspective.

## Markdown editor

`https://markdown.new/markdown-editor` loaded with:

- a large Markdown textbox
- `Clear`
- `Copy`
- `Download`
- preview controls shown as `◀`, `⬛`, and `▶`

The default document included headings, bullet lists, and a table. This page is a utility editor, not part of the conversion API.

## Practical guidance

1. Use browser pages when the user explicitly wants the hosted UI.
2. Use raw HTTP calls when the user wants repeatable automation.
3. If browser automation against the homepage is flaky, jump straight to a path-prefix URL or `POST /`.
4. Treat `/markdown-editor` as separate from the conversion service. It helps write Markdown; it does not replace URL, file, or crawl endpoints.

## Useful browser shortcuts

- Single page conversion: `https://markdown.new/https://example.com`
- Crawl shortcut: `https://markdown.new/crawl/https://example.com`
- Editor: `https://markdown.new/markdown-editor`

See also `references/url-conversion.md`, `references/file-conversion.md`, and `references/crawl.md`.
