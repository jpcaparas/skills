# Runtime and Browser Workflow

Use this reference when a production URL is available or when the user asked for a live-site-aware audit.

## Inspection Order and Browser Evidence

Choose source, HTTP, and browser inspection order according to the evidence needed and the user's explicit instructions. A browser-first request governs that audit; it is not a global prerequisite. Independent work may proceed in parallel.

Use a rendered browser check before claiming browser-agent usability or runtime WebMCP support. Read the available tool's harness guidance first; no particular browser skill name is required. Source matches, HTTP checks, and scanner output cannot establish rendered browser usability on their own.

## Resolve the Target

When live verification is needed and the production target is missing or ambiguous, ask a concise question, for example:

`What production URL should I audit for this repository?`

Clarify multiple deployed surfaces when necessary. Continue source work independently, and do not request a URL solely to satisfy a source-only audit.

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

Use the packaged helper when an external scan is in scope and authorized. Submitting a URL discloses it to a third party. Get consent for private, staging, internal, or credential-bearing targets before submitting; never send credentials, cookies, or signed URL tokens. Use authorized direct checks or source assessment if disclosure is not approved.

```bash
python3 scripts/scan_site.py --url https://example.com --output <report-dir>/scan-results.json
```

The helper's endpoint and response shape are a historical baseline, verified against `https://example.com` on April 19, 2026, not a guarantee of the current API. That response included:

- `level`
- `levelName`
- `checks`
- `nextLevel`

That response also showed probes of multiple candidate paths for MCP server cards and Agent Skills discovery. When the endpoint or schema differs, consult current official documentation, record the observed version/date, and report any unsupported helper contract rather than inventing parameters or results.

## How to Read Runtime Results

Use these rules:

- If runtime passes and source agrees, mark the signal as `pass`.
- If runtime fails but source appears to implement the signal, suspect deployment drift or incorrect exposure.
- If runtime is blocked and source looks plausible, mark deployed status `unknown` and assess source status separately, not as a deployed `pass`.
- If runtime returns `neutral`, preserve that in the report and explain why.
- A scan proves only what the scanner reported for that target and time. Reconcile it with direct HTTP, browser, and source evidence; retain both observations when they disagree.

## Browser-Specific Notes

- Verify WebMCP against the target browser and protocol version. The April 2026 registration example in `references/signal-map.md` is not an evergreen definition of all implementations.
- Auth-protected flows may hide `.well-known` or API metadata behind redirects. Note the redirect behavior instead of assuming absence.
- For content negotiation, check both the raw response headers and the actual returned content type.
- Keep verification read-only. Do not submit forms, invoke mutating tools, weaken secure headers, or bypass access controls to get a passing readiness result.

## When No Browser Skill Exists

Use authorized direct HTTP checks, an optional authorized scan, and source inspection for the aspects they can prove.

Call out the missing browser pass in the report so the user knows WebMCP and rendered behavior were not fully verified.
