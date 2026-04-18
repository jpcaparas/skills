---
name: isitagentready
description: "Audit a repository against Cloudflare's agent-readiness signals from isitagentready.com and the April 17, 2026 Cloudflare launch post, then write a detailed markdown report packet. Use when the user asks for /isitagentready, an agent-readiness audit, AI agent readiness, robots.txt/llms.txt/markdown negotiation readiness, MCP or API catalog discovery readiness, OAuth discovery readiness, WebMCP readiness, or a repo-level review of whether a deployed site works well for AI agents. If a production URL exists and a headless browser skill is available, ask for the URL, run the browser pass first, then inspect source. Do NOT trigger for generic SEO audits, direct implementation-only requests, or single-standard questions that do not require a repository audit."
compatibility: "Requires: python3. Optional: network access for `scripts/scan_site.py`, and `{{ skill:agent-browser }}` for rendered production-site verification."
---

# isitagentready

Audit a live repository against Cloudflare's agent-readiness checks, then write a fix-ready markdown report packet grounded in runtime evidence and source inspection.

## Decision Tree

What do you need to do?

- Run the full audit and create the report packet
  - Read `references/methodology.md`
  - Run `python3 scripts/create_report_packet.py --repo .`
  - Then read `references/signal-map.md`

- Understand the full Cloudflare signal inventory, score boundaries, and applicability rules
  - Read `references/signal-map.md`
  - Then read `references/shared.md`

- Verify the live production site before source inspection
  - Read `references/runtime-and-browser.md`
  - If a browser skill is available, load `{{ skill:agent-browser }}`

- Search the repository surgically for likely implementations, gaps, or deployment clues
  - Read `references/repo-search-playbook.md`

- Write the final markdown report in the expected format
  - Read `references/report-format.md`
  - Use `templates/agent-readiness-report.md`

- Avoid false positives, score inflation, or applicability mistakes
  - Read `references/gotchas.md`

## Quick Reference

| Task | Use | Outcome |
| --- | --- | --- |
| Create a report packet in the repo root | `python3 scripts/create_report_packet.py --repo . --url https://example.com` | Creates a timestamped folder with `agent-readiness-report.md`, `sources.md`, and `metadata.json` |
| Fetch the official `isitagentready.com` scan JSON for a deployed URL | `python3 scripts/scan_site.py --url https://example.com --output ./isitagentready-report/scan-results.json` | Saves the raw scan JSON for evidence and score context |
| Run the audit workflow in the right order | `references/methodology.md` | Browser/runtime check first, repo inspection second, report synthesis last |
| Map repo evidence to Cloudflare checks | `references/signal-map.md` + `references/repo-search-playbook.md` | Per-signal pass/fail/partial/not-applicable assessment |
| Write the final report | `references/report-format.md` + `templates/agent-readiness-report.md` | Detailed markdown report with evidence, coverage, and remediation order |
| Validate the packaged skill | `python3 scripts/validate.py skills/isitagentready` | Structural validation |
| Test the packaged skill | `python3 scripts/test_skill.py skills/isitagentready` | Cross-reference, eval, and helper-script checks |

## Core Workflow

1. Resolve the repository root first. This skill is meant to run inside repositories, not against arbitrary URLs in isolation.
2. Ask one direct question when the production URL is missing and live verification is possible: `What production URL should I audit for this repository?`
3. If a production URL exists and `{{ skill:agent-browser }}` is available, load it and complete the browser pass before opening source files. Wait for that pass to finish; use it to anchor the later code review.
4. Create the local report packet with `python3 scripts/create_report_packet.py --repo <repo> [--url <production-url>]`.
5. If network access is available, fetch the official Cloudflare-style scan JSON with `python3 scripts/scan_site.py --url <production-url> --output <report-dir>/scan-results.json`.
6. Inspect the repository for every scored and supporting signal. Search static files, route handlers, middleware, CDN config, edge config, and deployment transforms before concluding a signal is missing.
7. Separate findings into four buckets:
   - Confirmed in production
   - Present in source but not yet proven deployed
   - Missing or contradicted by source/runtime evidence
   - Not applicable or currently neutral
8. Write `agent-readiness-report.md` with concrete evidence, applicability reasoning, and a prioritized remediation order. Do not leave the report as a checklist dump.

## Audit Deliverables

Produce these artifacts in the report packet:

1. **Executive summary** — what materially limits agent readiness right now.
2. **Evidence sources** — browser pass, official scan JSON, repo inspection, and unresolved areas.
3. **Official scan snapshot** — only when a live URL was scanned. Include `level`, `levelName`, and `nextLevel` if present.
4. **Findings by category** — discoverability, content, bot access control, protocol discovery, and commerce/supporting signals.
5. **Applicability decisions** — why a signal is scored, neutral, or not applicable for this repo.
6. **Repository coverage map** — which files, routes, configs, and deployment layers were inspected.
7. **Prioritized remediation** — what to fix first, second, and later.

## Analysis Rules

1. Treat the Cloudflare runtime scan as authoritative for deployed behavior, but never let it replace repository inspection. Many failures are deployment drift, not missing code.
2. Do not invent an official Cloudflare level from source code alone. Without a live scan, produce a repository assessment, not a claimed score.
3. Ask for the production URL before the browser step. Do not silently guess from package metadata, DNS, or README files unless the user already stated the deployment target.
4. Mark optional or neutral checks explicitly. A static content site should not be penalized for lacking commerce flows or OAuth protected resource metadata unless the product genuinely exposes those capabilities.
5. Search deployment surfaces, not just app code. Headers and well-known routes are often emitted by CDN rules, edge middleware, or reverse proxies.
6. Distinguish `missing in source`, `present but unverified`, and `failing in production`. Those are different remediation paths.

## Reading Guide

| If the task is... | Read |
| --- | --- |
| Full audit from repo to report packet | `references/methodology.md`, then `references/report-format.md` |
| Understand Cloudflare's checks and how they map to code | `references/signal-map.md` |
| Run browser-first/live-site verification | `references/runtime-and-browser.md` |
| Search the repo for likely implementations or deployment clues | `references/repo-search-playbook.md` |
| Avoid mis-scoring optional or neutral checks | `references/shared.md` and `references/gotchas.md` |

## Verified External Baseline

This skill was grounded against current primary Cloudflare sources retrieved on April 19, 2026:

- `https://isitagentready.com/`
- `https://blog.cloudflare.com/agent-readiness/` published April 17, 2026
- `https://isitagentready.com/.well-known/agent-skills/index.json`
- Representative `SKILL.md` documents published by `isitagentready.com` for robots.txt, sitemap, link headers, markdown negotiation, content signals, Web Bot Auth, API Catalog, OAuth discovery, OAuth Protected Resource metadata, MCP Server Card, A2A Agent Card, Agent Skills discovery, WebMCP, x402, UCP, and ACP

Use the references in this skill as the first source of truth, then verify live details when the target stack, deployment layer, or browser surface has changed.

## Gotchas

1. **Ask for the production URL before the browser pass**: this skill is explicitly browser-first when a live site and headless browser are available.
2. **Do not claim an official Cloudflare score without a live scan**: code inspection alone is not the same as the deployed score returned by `isitagentready.com`.
3. **Commerce does not currently count toward the score**: the April 17, 2026 Cloudflare blog states that x402, UCP, and ACP are checked but do not currently contribute to the score.
4. **`llms.txt` is adjacent, not the same as markdown negotiation**: Cloudflare's default score checks markdown negotiation; `llms.txt` and `llms-full.txt` are useful supporting signals and may appear in customized scans.
5. **Headers often live outside the app**: missing `Link` or `Content-Type: text/markdown` behavior may be implemented in CDN, edge, or proxy config rather than route code.
6. **A wildcard robots rule is insufficient for AI-specific bot rules**: Cloudflare's `ai-rules` skill explicitly expects named AI crawler blocks.
7. **WebMCP must be verified in a rendered page**: source search helps, but the check is effectively a browser/runtime behavior.

## Helper Files

- `references/shared.md` — shared terminology, scoring boundaries, and source baseline.
- `references/methodology.md` — end-to-end audit workflow and evidence model.
- `references/signal-map.md` — full Cloudflare signal inventory with applicability notes.
- `references/runtime-and-browser.md` — production URL handling, browser-first workflow, and scan API usage.
- `references/repo-search-playbook.md` — surgical search heuristics across frameworks and deployment layers.
- `references/report-format.md` — the exact output packet layout and report contract.
- `references/gotchas.md` — common traps and misreadings.
- `templates/agent-readiness-report.md` — starting template for the markdown report.
- `scripts/create_report_packet.py` — deterministic report-packet scaffolder.
- `scripts/scan_site.py` — helper to fetch the live `isitagentready.com` scan JSON.
- `scripts/validate.py` — structural validator for this skill.
- `scripts/test_skill.py` — packaging, eval, and helper-script test runner.
