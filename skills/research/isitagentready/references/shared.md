# Shared Conventions

## Scope

This file defines the shared language and scoring boundaries for `isitagentready`.

The authoritative external baseline for this skill is Cloudflare's `isitagentready.com` site plus the Cloudflare blog post published on April 17, 2026:

- `https://isitagentready.com/`
- `https://blog.cloudflare.com/agent-readiness/`

Use these shared conventions before reading the deeper workflow and per-signal references.

## Terminology

| Term | Meaning |
| --- | --- |
| official scan | The runtime result returned by `https://isitagentready.com/api/scan` for a deployed URL, including `level`, `levelName`, `checks`, and `nextLevel` |
| repository assessment | The codebase-based analysis this skill produces when a live scan is unavailable or incomplete |
| production URL | The real deployed URL that corresponds to the repository being audited |
| scored signal | A check that contributes to the current score dimensions described in the Cloudflare blog |
| supporting signal | A useful adjacent signal, such as `llms.txt` or `llms-full.txt`, that informs readiness but may not be part of the default score |
| neutral signal | A check the official scan can return as informational or effectively optional for some site types |
| applicability | The reasoning for whether a signal should be treated as required, optional, neutral, or out of scope for the audited repo |

## Shared Setup

1. Resolve the repository root before creating files or drawing conclusions.
2. Ask the user for the production URL when live verification is possible and they did not already provide it.
3. Prefer a browser-first pass when `{{ skill:agent-browser }}` is available.
4. Create the report packet locally with `python3 scripts/create_report_packet.py --repo . [--url ...]`.
5. Use `python3 scripts/scan_site.py --url <production-url> --output <report-dir>/scan-results.json` when network access is available.
6. Keep runtime evidence, repo evidence, and unknowns separate in the report.

## Score Boundaries

Cloudflare's April 17, 2026 launch post says the current score is based on four dimensions:

- Discoverability
- Content
- Bot Access Control
- Capabilities

The same post also says commerce checks are evaluated but do not currently count toward the score.

Do not flatten everything into a single yes/no readiness answer. Preserve the category boundaries and note when a signal is currently non-scoring, optional, or neutral.

## Status Vocabulary

Use these labels consistently in the report:

| Status | Meaning |
| --- | --- |
| pass | Confirmed in production or directly evidenced in repo and consistent with expected behavior |
| partial | Some implementation exists, but it is incomplete, inconsistent, or unverified in production |
| fail | Missing, contradicted, or clearly non-compliant |
| neutral | Informational only for this site type, or reported as neutral by the official scan |
| not applicable | The product does not expose the capability the signal is meant to describe |
| unknown | Evidence was blocked or insufficient; more runtime verification is needed |

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
- `llms.txt` and `llms-full.txt` are useful signals, but Cloudflare's default score emphasizes markdown negotiation instead.
