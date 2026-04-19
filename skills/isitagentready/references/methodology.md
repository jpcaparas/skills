# Methodology

## Goal

Produce a detailed markdown report packet that explains whether a repository abides by Cloudflare's agent-readiness signals, what was proven in production, what was only found in source, what remains unverified, and what should be fixed first.

## Workflow

Follow these stages in order. Do not skip the browser or live-site step when a production URL and browser tooling are available.

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

If the user did not supply a production URL and live verification is possible, ask exactly one short question before source inspection:

`What production URL should I audit for this repository?`

Do this before browsing source code when `{{ skill:agent-browser }}` or networked runtime validation is available. The user explicitly asked for the browser step to happen before source analysis.

### Stage 3: Create the Report Packet

Run:

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

### Stage 4: Browser-First Live Verification

If a production URL exists and `{{ skill:agent-browser }}` is available:

1. Load `{{ skill:agent-browser }}`.
2. Complete a rendered browser pass before opening source files.
3. Capture evidence for:
   - homepage response behavior
   - visible or hidden `.well-known` routes
   - WebMCP registration
   - auth gating
   - content rendering that may affect markdown or bot access
4. Finish this pass and record the outcome before moving into repo inspection.

If a browser skill is not available, fall back to the official scan API plus direct HTTP checks.

### Stage 5: Fetch the Official Scan JSON

If network access is available and you have a production URL, run:

```bash
python3 scripts/scan_site.py --url https://example.com --output <report-dir>/scan-results.json
```

Capture at least these fields in the report when present:

- `level`
- `levelName`
- `nextLevel`
- `checks.*`

Treat the official scan as runtime truth for deployed behavior. Do not discard it because the repo looks better on paper.

### Stage 6: Inspect the Repository

Use `references/repo-search-playbook.md` to inspect, at minimum:

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
| runtime fail + repo evidence | deployment drift or incorrect wiring | inspect deployment config or route exposure |
| runtime unknown + repo evidence | likely implemented but unverified | request live access or staging verification |
| runtime fail + no repo evidence | missing implementation | add the feature |
| neutral or not applicable | deliberate omission | document the rationale |

When a split repository exposes backend OpenAPI or MCP configuration but the user-supplied production URL is a separate public web app, record that as `present in source` or `runtime unverified` until the deployed surface exposes or links the capability.

### Stage 8: Write the Report

Open `templates/agent-readiness-report.md`, then replace its placeholders and comments with real findings.

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

Do not finish the audit without all of these:

1. Executive summary
2. Category-by-category findings
3. Applicability decisions
4. Repo coverage map
5. Prioritized remediation

## Escalation Rules

- If the repository clearly maps to more than one deployed surface, ask which production URL is authoritative.
- If the live site is behind auth and the user does not provide access, continue with repo inspection but mark runtime-dependent signals as `unknown`.
- If the repo contains deployment config for one platform but production behaves differently, call out the mismatch instead of guessing which source is canonical.
