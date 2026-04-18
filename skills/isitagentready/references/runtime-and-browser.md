# Runtime and Browser Workflow

Use this reference when a production URL is available or when the user asked for a live-site-aware audit.

## Browser-First Rule

If both of these are true:

- the repository has a real production URL
- a headless browser skill is available

then the browser pass comes before source inspection.

The requested order is:

1. ask for the production URL if missing
2. load `{{ skill:agent-browser }}`
3. complete the browser pass
4. only then inspect source code

Do not reverse the order unless the user explicitly blocks browser work.

## The One Question

When the production URL is not already provided, ask:

`What production URL should I audit for this repository?`

Keep it to that one question unless multiple deployed surfaces genuinely require clarification.

## Live-Site Evidence to Capture

Capture evidence for these runtime behaviors:

- homepage status, content type, and `Link` headers
- `GET /robots.txt`
- `GET /sitemap.xml`
- `GET /llms.txt` and `GET /llms-full.txt` when relevant
- `Accept: text/markdown` behavior on representative pages
- `.well-known` discovery documents
- auth gates or redirects
- WebMCP registration in a rendered browser

## Official Scan API

Use the packaged helper when network access is allowed:

```bash
python3 scripts/scan_site.py --url https://example.com --output <report-dir>/scan-results.json
```

The live API call was verified during skill creation against `https://example.com` on April 19, 2026. The response included:

- `level`
- `levelName`
- `checks`
- `nextLevel`

The response also showed that the scanner can probe multiple candidate paths for some checks, such as MCP server cards and Agent Skills discovery.

## How to Read Runtime Results

Use these rules:

- If runtime passes and source agrees, mark the signal as `pass`.
- If runtime fails but source appears to implement the signal, suspect deployment drift or incorrect exposure.
- If runtime is blocked and source looks plausible, mark `unknown` or `partial`, not `pass`.
- If runtime returns `neutral`, preserve that in the report and explain why.

## Browser-Specific Notes

- WebMCP is best validated through a rendered page because the registration happens in browser code.
- Auth-protected flows may hide `.well-known` or API metadata behind redirects. Note the redirect behavior instead of assuming absence.
- For content negotiation, check both the raw response headers and the actual returned content type.

## When No Browser Skill Exists

Fall back to:

1. `python3 scripts/scan_site.py`
2. direct HTTP checks for the obvious well-known routes
3. source inspection

Call out the missing browser pass in the report so the user knows WebMCP and rendered behavior were not fully verified.
