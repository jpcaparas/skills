# Report Format

Use this reference when writing the final markdown analysis.

## Output Packet

Create the packet with:

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

## Required Report Sections

The final `agent-readiness-report.md` must contain:

1. `# Agent Readiness Analysis: <repo>`
2. `## Executive Summary`
3. `## Evidence Sources`
4. `## Official Scan Snapshot`
5. `## Findings by Category`
6. `## Applicability Decisions`
7. `## Repository Coverage`
8. `## Prioritized Remediation`
9. `## Open Questions`

Use `templates/agent-readiness-report.md` as the starting point.

## Writing Contract

The report must:

- preserve Cloudflare's category boundaries
- say whether each finding came from runtime, repo, or both
- note when a check is supporting-only or non-scoring
- keep unresolved items visible
- prioritize fixes instead of ending with a flat checklist
- use repo-relative paths in the markdown report instead of absolute local filesystem paths

## Minimum Table Shape

Inside `## Findings by Category`, each category table should include:

- signal
- applicability
- status
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

## Sources File

Leave `sources.md` intact and append any additional live URLs or relevant RFC links if the audit relied on them.

## Metadata File

Keep `metadata.json` as the machine-readable summary of:

- repo path
- report path
- production URL
- created timestamp
- source URLs

If `scan-results.json` is created later, do not forget to mention it in the report's evidence section.
