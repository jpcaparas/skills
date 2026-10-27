# exa-efficiency

Production skill for using Exa (exa.ai) at the lowest sensible cost, with a script that prices requests before they are sent. The authoritative instructions live in `SKILL.md`.

## What It Covers

- Hard rules: override the costly defaults (`auto` search type, full-text `/contents`, uncapped metered Agent runs), price before spending, confirm open-ended spend
- The cheapest route per job: `lite` search with highlights, `/answer`, free `outputSchema` synthesis on `auto`, `deep-lite`, single-view `/contents`, fixed-effort Agent runs, capped `auto` runs, manual-first monitors, the keyless MCP
- Traps: `lite` parameter rejections, per-view `/contents` billing, Agent contact and Connect charges, cancel discarding results, monitors that report no cost, Enterprise-only batches
- Context efficiency: response sizes measured live and how to bound them
- Every price checked against `costDollars` from 60 live requests on 2026-10-27

## Key Files

- `SKILL.md` for the authoritative instructions
- `references/pricing.md`, `references/recipes.md`, `references/account-guards.md`, `references/gotchas.md`, `references/evidence.md`
- `scripts/exa_cost.py` for offline worst-case and monthly cost estimates
- `scripts/test_helper.py` for offline regressions built from the live-billed amounts
