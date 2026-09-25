# Report Format

Use this reference when choosing the response form. Match the user's requested scope and format; a short diagnosis with evidence, applicability, and limits is sufficient for a single-signal readiness audit.

## Optional Output Packet

Create files only when requested. If a packet is useful, optionally scaffold it with:

```bash
python3 scripts/create_report_packet.py --repo . --url https://example.com
```

Default output layout:

```text
<repo-root>/isitagentready-<repo-slug>-<timestamp>/
  agent-readiness-report.md
  metadata.json
  sources.md
  scan-results.json   # optional, created later if a live scan is run
```

## Suggested Full-Report Sections

A full report normally covers these topics; combine, rename, or omit headings to fit the request without losing relevant evidence or limitations:

1. `# Agent Readiness Analysis: <repo>`
2. `## Executive Summary`
3. `## Evidence Sources`
4. `## Official Scan Snapshot` — only if a scan ran; include target, timestamp, and reported version when available
5. `## Findings by Category`
6. `## Applicability Decisions`
7. `## Repository Coverage`
8. `## Prioritized Remediation`
9. `## Open Questions`

Use `templates/agent-readiness-report.md` as an optional starting point. If no scan ran, state that the official score is unverified under evidence or limitations, not in a fabricated snapshot. No helper, packet, or fixed heading count is required.

## Writing Contract

The report must:

- preserve Cloudflare's category boundaries
- say whether each finding came from runtime, repo, or both
- distinguish source status from deployed status; a source pass does not imply deployment
- note supporting-only or non-scoring checks against the measured scan/version, not an assumed permanent scoring rule
- retain disagreements between scan, HTTP, browser, and source observations, including dates and request context
- keep unresolved items visible
- prioritize fixes instead of ending with a flat checklist
- use repo-relative paths in the markdown report instead of absolute local filesystem paths

## Suggested Table Shape

When tables are useful, include:

- signal
- applicability
- source status and deployed status separately
- runtime evidence
- repository evidence
- fix direction

Keep the signal names aligned to the official keys where practical:

- `robotsTxt`
- `sitemap`
- `linkHeaders`
- `markdownNegotiation`
- `robotsTxtAiRules`
- `contentSignals`
- `webBotAuth`
- `apiCatalog`
- `oauthDiscovery`
- `oauthProtectedResource`
- `mcpServerCard`
- `a2aAgentCard`
- `agentSkills`
- `webMcp`
- `x402`
- `ucp`
- `acp`

Supporting signals can be reported with human-readable names:

- `llms.txt`
- `llms-full.txt`

## Executive Summary Expectations

The summary should answer:

- Is the deployed site clearly agent-ready, partially ready, or blocked by foundational gaps?
- Which 2-4 issues matter most?
- Are the gaps code, deployment, or unknown?

## Applicability Expectations

Do not hide applicability in footnotes. If a signal is not applicable or neutral:

- say that explicitly
- explain why
- avoid treating the absence as a failing implementation

## Sources File (When Requested)

If a packet was created, distinguish the bundled baseline URLs in `sources.md` from sources actually consulted. Append relevant current official sources with versions or retrieval dates; a prefilled link is not proof it was read.

## Metadata File (When Requested)

Keep `metadata.json` as the machine-readable summary of:

- repo path
- report path
- production URL
- created timestamp
- source URLs

If `scan-results.json` is created later, do not forget to mention it in the report's evidence section.
