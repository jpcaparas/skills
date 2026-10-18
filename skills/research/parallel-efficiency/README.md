# parallel-efficiency

Production skill for using Parallel (parallel.ai) at the lowest sensible cost, with a script that prices requests before they are sent. The authoritative instructions live in `SKILL.md`.

## What It Covers

- Hard rules: override every expensive default (Search `advanced`, Responses `medium`, FindAll enrichments on `core`, CLI `pro`), price before spending, confirm large or open-ended spend
- The cheapest product per job: fast Search, Extract excerpts, low-effort Responses, the processor ladder for Tasks, Entity Search before FindAll, preview-then-extend FindAll, slow lite Monitors
- Traps: uncancellable Task runs, notify-only spend limits, FindAll per-match multipliers, monitors that bill when nothing changes, up-front Task Group reservations
- Context efficiency: excerpt budgets, objectives, and session reuse
- Every request shape checked against Parallel's OpenAPI spec on 2026-10-18

## Key Files

- `SKILL.md` for the authoritative instructions
- `references/pricing.md`, `references/recipes.md`, `references/account-guards.md`, `references/gotchas.md`, `references/evidence.md`
- `scripts/parallel_cost.py` for offline worst-case and monthly cost estimates
- `scripts/test_helper.py` for offline regressions computed from the pricing page
