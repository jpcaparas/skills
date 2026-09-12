# File Conversion

Use this reference when the input is a file URL or a local file that should become Markdown.

## Supported flows

| Flow | Endpoint | Verified on April 9, 2026 | Notes |
| --- | --- | --- | --- |
| Remote file URL as GET | `GET /<file-url>?format=json` | Yes | Works well for raw GitHub files and CSV |
| Remote file URL as POST | `POST /` with `{"url":"https://example.com/report.pdf"}` | Indirectly verified | Same route family as page conversion |
| Local file upload | `POST /convert` with multipart form data | Yes | Tested with a local `.md` file |

The file converter is documented at `https://markdown.new/file-to-markdown`.

## Documented limits

The site documents:

- No authentication required
- 500 requests per day per IP
- Maximum file size: 10 MB
- URL-based fetch timeout: 30 seconds

## Verified examples

### Raw Markdown file from GitHub

```bash
curl -s 'https://markdown.new/https://raw.githubusercontent.com/github/gitignore/main/README.md?format=json'
```

Observed result:

- `success: true`
- `method: Workers AI (file)`
- Clean Markdown content from the raw README

### CSV file from a remote URL

```bash
curl -s 'https://markdown.new/https://raw.githubusercontent.com/cs109/2014_data/master/countries.csv?format=json'
```

Observed result:

- `title: countries.csv`
- `content` wrapped the file body in a fenced `csv` block
- `method: Workers AI (file)`

### Local upload

```bash
tmp=$(mktemp /tmp/markdown-new-upload-XXXX.md)
printf '# Upload Test\n\n- one\n- two\n' > "$tmp"
curl -s -X POST 'https://markdown.new/convert' -F "file=@$tmp"
rm -f "$tmp"
```

Observed JSON shape:

```json
{
  "success": true,
  "data": {
    "title": "Upload Test",
    "content": "# Upload Test\n\n- one\n- two\n",
    "filename": "markdown-new-upload-XXXX.md",
    "file_type": ".md",
    "file_size": 27,
    "processing_time_ms": 0
  }
}
```

## Response shapes

### Remote URL response

Remote file URLs follow the same top-level JSON shape as page conversion:

```json
{
  "success": true,
  "url": "https://raw.githubusercontent.com/github/gitignore/main/README.md",
  "title": "A collection of `.gitignore` templates",
  "content": "# A collection of `.gitignore` templates\n\n...",
  "timestamp": "2026-04-09T08:29:26.058Z",
  "method": "Workers AI (file)",
  "duration_ms": 251
}
```

### Local upload response

Local uploads return `success` plus a nested `data` object:

- `title`
- `content`
- `filename`
- `file_type`
- `file_size`
- `processing_time_ms`

Do not assume uploads will return the same top-level keys as URL-based conversions.

## Source-type guidance

| Input | Best route |
| --- | --- |
| Public PDF/DOCX/XLSX/image URL | `GET /<url>?format=json` or `POST /` |
| Raw GitHub file URL | `GET /<url>?format=json` |
| Local file on disk | `POST /convert` |
| GitHub `blob` page | Do not use as a file source; switch to the raw URL |
| `.html` or `.htm` URL | Treat as a page URL unless you explicitly want file semantics |

The site documents one subtle split:

- Uploaded `.html` or `.htm` files use the file pipeline.
- URL-based `.html` sources use the webpage pipeline.

## Documented file coverage

The site groups formats like this:

- Documents: `.pdf`, `.docx`, `.odt`
- Spreadsheets: `.xlsx`, `.xls`, `.xlsm`, `.xlsb`, `.et`, `.ods`, `.numbers`
- Images: `.jpg`, `.jpeg`, `.png`, `.webp`, `.svg`
- Text and data: `.txt`, `.md`, `.csv`, `.json`, `.xml`, `.html`, `.htm`

The page says image conversion uses AI models to describe the visual content. That behavior was documented but not directly tested here.

## Practical rules

1. If the source is already a raw file URL, use that directly.
2. If the source is a GitHub page view, convert it to a raw URL first.
3. If the file is local, use `POST /convert`.
4. If response shape matters, normalize URL-mode and upload-mode results in your caller because they are not identical.

## Helper script

```bash
python3 scripts/probe_markdown_new.py --mode get 'https://raw.githubusercontent.com/github/gitignore/main/README.md' --json-response
python3 scripts/probe_markdown_new.py --mode upload ./notes.md
```

See also `references/gotchas.md` for response-shape and blob-vs-raw pitfalls.
