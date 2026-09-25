# Shared Conventions

## Scope

This file defines the shared language and scoring boundaries for `isitagentready`.

The historical external baseline for this skill is Cloudflare's `isitagentready.com` site retrieved April 19, 2026, plus the blog post published April 17, 2026:

- `https://isitagentready.com/`
- `https://blog.cloudflare.com/agent-readiness/`

Use these shared conventions before reading the deeper workflow and per-signal references.

## Terminology

| Term | Meaning |
| --- | --- |
| official scan | The scanner's reported result for a URL and time; the April 2026 API used `https://isitagentready.com/api/scan` and fields including `level`, `levelName`, `checks`, and `nextLevel` |
| repository assessment | The codebase-based analysis this skill produces when a live scan is unavailable or incomplete |
| production URL | The real deployed URL that corresponds to the repository being audited |
| scored signal | A check contributing to the score in the recorded scanner version or dated scoring documentation |
| supporting signal | A useful adjacent signal, such as `llms.txt` or `llms-full.txt`, that informs readiness but may not be part of the default score |
| neutral signal | A check the official scan can return as informational or effectively optional for some site types |
| applicability | The reasoning for whether a signal should be treated as required, optional, neutral, or out of scope for the audited repo |

## Shared Setup

1. Resolve the repository root before creating files or drawing conclusions.
2. Ask for a missing or ambiguous production URL when live verification is needed; continue independent source work.
3. Choose inspection order by evidence needs and explicit user instructions; require rendered browser evidence for browser-usability claims.
4. Create files only when requested; `scripts/create_report_packet.py` is optional.
5. Use `scripts/scan_site.py` only for an authorized external scan, with consent before disclosing private targets and without transmitting credentials.
6. Keep runtime evidence, repo evidence, and unknowns separate in the report.

## Score Boundaries

Cloudflare's April 17, 2026 launch post described four score dimensions:

- Discoverability
- Content
- Bot Access Control
- Capabilities

That post described commerce checks as evaluated but non-scoring. Treat these dimensions and weights as a dated baseline; use the actual scan snapshot and current official documentation for a current scoring claim. If no version is exposed, record the scan time and say the version was not reported.

Do not flatten everything into a single yes/no readiness answer. Preserve the category boundaries and note when a signal is currently non-scoring, optional, or neutral.

## Status Vocabulary

Record source status and deployed status separately. For example, `source: pass; deployed: unknown` means implementation evidence exists but deployment has not been verified. Use these labels with their evidence scope:

| Status | Meaning |
| --- | --- |
| pass | Confirmed by evidence at the named layer; a deployed pass needs runtime evidence, and browser usability needs rendered browser evidence |
| partial | The assessed layer is demonstrably incomplete or inconsistent; do not use this merely to hide an unverified deployment |
| fail | Missing or contradicted at the assessed layer; absent source alone is not a deployed failure |
| neutral | Informational only for this site type, or reported as neutral by the official scan |
| not applicable | The product does not expose the capability the signal is meant to describe |
| unknown | Evidence at this layer was blocked, not collected, or insufficient |

## Navigation Guide

- Read `references/methodology.md` for the full audit flow.
- Read `references/signal-map.md` for the full Cloudflare signal inventory.
- Read `references/runtime-and-browser.md` for the production URL rule and live-site workflow.
- Read `references/repo-search-playbook.md` when you need exact places to look in a codebase.
- Read `references/report-format.md` when writing the output packet.
- Read `references/gotchas.md` when a result feels ambiguous or too easy.

## Cross-Cutting Gotchas

- A live scan failure can still be a deployment or CDN issue even when the repo has the right code.
- A source-code hit does not prove the deployed site exposes the behavior.
- In the April 2026 baseline, Cloudflare's default score emphasized markdown negotiation rather than `llms.txt` and `llms-full.txt`. These are distinct behaviors regardless of scoring changes.
