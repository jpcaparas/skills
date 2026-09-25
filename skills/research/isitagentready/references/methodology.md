# Methodology

## Goal

Explain readiness for the signals in scope: what was proven in production, what was only found in source, what remains unverified, and what should be fixed first. Match the user's requested response form; create a report packet only when files are requested.

## Workflow

These stages are a planning guide, not a fixed inspection order. Honor explicit user ordering; otherwise choose the sequence that best resolves uncertainty, and run independent source, HTTP, and browser checks in parallel. Obtain runtime evidence before making runtime claims, regardless of when source inspection happens.

### Stage 1: Resolve Scope

1. Resolve the repository root.
2. Identify the app surfaces that matter:
   - homepage or primary landing route
   - docs or content routes
   - API routes
   - auth flows
   - commerce or checkout routes
   - any `.well-known` endpoints
   - separate web and API apps that may deploy independently
3. Decide whether the repo is primarily:
   - content site
   - API or application
   - mixed product

### Stage 2: Ask for the Production URL

If live verification is needed and the production URL is missing or ambiguous, ask a concise question to identify the target. For example:

`What production URL should I audit for this repository?`

Continue independent source work while the target is unresolved. A source-only request does not require a URL. Never guess which app or deployment to scan.

### Stage 3: Optionally Create the Report Packet

If the user requests report files, the helper can scaffold them:

```bash
python3 scripts/create_report_packet.py --repo . --url https://example.com
```

The script creates a visible timestamped folder under the repository root by default:

```text
<repo-root>/isitagentready-<repo-slug>-<timestamp>/
  agent-readiness-report.md
  metadata.json
  sources.md
```

Use the printed `output_dir` for any later `scan-results.json` file.

### Stage 4: Live Verification

When a production URL and authorized browser tooling are available, use a browser for rendered behavior in scope:

1. Load the browser tool's harness guidance.
2. Inspect representative pages; source inspection may guide which ones to check.
3. Capture evidence for:
   - homepage response behavior
   - visible or hidden `.well-known` routes
   - WebMCP registration
   - auth gating
   - content rendering that may affect markdown or bot access
4. Record observations and browser/version context before claiming browser usability or rendered WebMCP support.

If browser access is unavailable or out of scope, use authorized HTTP and source checks, but label browser-dependent behavior unverified. HTTP or scan results do not substitute for a rendered browser usability check.

### Stage 5: Fetch the Official Scan JSON

If an external scan is in scope and authorized, optionally run the helper below. Before submitting private, staging, internal, or credential-bearing URLs, obtain consent to disclose the target to `isitagentready.com`; never send credentials or signed query tokens. Network access alone is not consent.

```bash
python3 scripts/scan_site.py --url https://example.com --output <report-dir>/scan-results.json
```

Capture at least these fields in the report when present:

- `level`
- `levelName`
- `nextLevel`
- `checks.*`

Keep the URL, scan time, and reported version if available. The scan establishes what the scanner reported at that time, not infallible deployed truth. Compare it with direct HTTP/browser evidence and source; preserve discrepancies and investigate differences in URL, timing, deployment, user agent, or auth rather than overwriting either observation.

### Stage 6: Inspect the Repository

Use `references/repo-search-playbook.md` to inspect relevant surfaces (all applicable ones for a full audit):

- static files in public or build output roots
- route handlers and middleware
- header injection code
- proxy or CDN config
- OAuth or OIDC configuration
- `.well-known` document generation
- browser-side scripts for WebMCP
- payment middleware or 402 handling

For each signal, collect:

- repo evidence: file paths, routes, config entries, or search hits
- runtime evidence: browser observations or scan JSON
- applicability note: required, optional, neutral, or not applicable
- note whether the authoritative production URL maps to the same app surface as the source evidence

### Stage 7: Reconcile Evidence

Classify each signal into one of these evidence patterns:

| Pattern | Meaning | Typical Fix Path |
| --- | --- | --- |
| runtime pass + repo evidence | implemented and deployed | no action or low-priority polish |
| runtime fail + repo evidence | possible deployment drift or incorrect wiring | inspect deployment config or route exposure |
| runtime unknown + repo evidence | source implementation found; deployment unverified | request live access or staging verification |
| runtime fail + no repo evidence | observed failure; implementation may be absent or external | inspect deployment ownership before proposing a change |
| scanner and direct runtime checks disagree | differing observations, not a resolved pass/fail | record both with time and request context; recheck the disputed behavior |
| neutral or not applicable | deliberate omission | document the rationale |

When a split repository exposes backend OpenAPI or MCP configuration but the user-supplied production URL is a separate public web app, record that as `present in source` or `runtime unverified` until the deployed surface exposes or links the capability.

### Stage 8: Write the Report

Use `references/report-format.md` for an adaptable full-report outline or a focused answer. If using `templates/agent-readiness-report.md`, replace placeholders with real findings and remove sections outside scope, including the scan snapshot when no scan ran.

The final report must:

- stay grounded in evidence
- preserve category boundaries
- call out applicability decisions
- separate live failures from source-only observations
- prioritize fixes instead of dumping an unordered checklist

## Evidence Standards

Use direct evidence whenever possible:

- concrete file paths
- exact endpoint paths
- specific headers or content types
- official scan JSON snippets summarized in your own words
- browser observations tied to exact URLs
- repo-relative paths in user-facing markdown, not absolute local filesystem paths

Avoid vague claims such as "probably supported" or "should work" unless you mark them as `unknown`.

## Minimum Deliverable Quality

For a full audit, normally include:

1. Executive summary
2. Category-by-category findings
3. Applicability decisions
4. Repo coverage map
5. Prioritized remediation
6. Evidence limits and unresolved disagreements

A scoped answer may combine these into a few paragraphs or a small table. Do not imply uninspected signals were audited.

## Escalation Rules

- If live verification is in scope and the repository maps to multiple deployed surfaces, clarify which production URL to assess.
- If the live site is behind auth and the user does not provide access, continue with repo inspection but mark runtime-dependent signals as `unknown`.
- If the repo contains deployment config for one platform but production behaves differently, call out the mismatch instead of guessing which source is canonical.
