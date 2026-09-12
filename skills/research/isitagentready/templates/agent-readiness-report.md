# Agent Readiness Analysis: {{REPO_NAME}}

| Field | Value |
| --- | --- |
| Repository | `{{REPO_NAME}}` |
| Production URL | {{PRODUCTION_URL}} |
| Created | {{CREATED_AT}} |
| Official scan JSON | `scan-results.json` if collected |

## Executive Summary

<!-- Summarize the repository's overall readiness, the biggest blockers, and whether the live scan or browser pass ran. -->

## Evidence Sources

- Repository inspection:
- Browser verification:
- Official `isitagentready.com` scan:
- Unverified or blocked areas:

## Official Scan Snapshot

| Field | Value |
| --- | --- |
| Level | |
| Level name | |
| Next level | |
| Commerce counted in score | No |

Leave this section explicit even when a live scan was unavailable.

## Findings by Category

### Discoverability

| Signal | Applicability | Status | Runtime evidence | Repository evidence | Fix direction |
| --- | --- | --- | --- | --- | --- |
| `robotsTxt` | | | | | |
| `sitemap` | | | | | |
| `linkHeaders` | | | | | |

### Content

| Signal | Applicability | Status | Runtime evidence | Repository evidence | Fix direction |
| --- | --- | --- | --- | --- | --- |
| `markdownNegotiation` | | | | | |
| `llms.txt` | | | | | |
| `llms-full.txt` | | | | | |

### Bot Access Control

| Signal | Applicability | Status | Runtime evidence | Repository evidence | Fix direction |
| --- | --- | --- | --- | --- | --- |
| `robotsTxtAiRules` | | | | | |
| `contentSignals` | | | | | |
| `webBotAuth` | | | | | |

### Capabilities / Discovery

| Signal | Applicability | Status | Runtime evidence | Repository evidence | Fix direction |
| --- | --- | --- | --- | --- | --- |
| `apiCatalog` | | | | | |
| `oauthDiscovery` | | | | | |
| `oauthProtectedResource` | | | | | |
| `mcpServerCard` | | | | | |
| `a2aAgentCard` | | | | | |
| `agentSkills` | | | | | |
| `webMcp` | | | | | |

### Commerce and Supporting Signals

| Signal | Applicability | Status | Runtime evidence | Repository evidence | Fix direction |
| --- | --- | --- | --- | --- | --- |
| `x402` | | | | | |
| `ucp` | | | | | |
| `acp` | | | | | |

## Applicability Decisions

<!-- Explain why any signal was marked neutral, not applicable, or supporting-only. -->

## Repository Coverage

Use repo-relative paths such as `apps/web/app/robots.ts` in this section. Do not copy absolute workstation paths into the report.

| Area | Files, routes, or config inspected | Notes |
| --- | --- | --- |
| Static and generated files | | |
| Route handlers and middleware | | |
| Edge or CDN config | | |
| Auth and identity config | | |
| Client-side runtime and browser hooks | | |
| Commerce or payment surfaces | | |

## Prioritized Remediation

1. 
2. 
3. 

## Open Questions

- 
