# firecrawl-efficiency

Production skill for getting content out of Firecrawl at the lowest credit cost, with a guard that prices requests before they are sent. The authoritative instructions live in `SKILL.md`.

## What It Covers

- Hard rules: never `/agent` or `/extract`, never premium or provider-routed hosts (X, LinkedIn)
- The cheapest route per job: scrape, search then scrape, map then batch scrape, bounded crawls, capped PDF parsing, interact, monitors
- Every credit multiplier, with live-measured prices from 2026-10-18 and the places Firecrawl's own docs disagree
- The 809-credit trap: crawls that bill query-string variants of one page, and the two flags that stop it
- Account guards: pay-as-you-go limits, overage allowance, per-key spend limits, forgotten monitors

## Key Files

- `SKILL.md` for the authoritative instructions
- `references/pricing.md`, `references/recipes.md`, `references/account-guards.md`, `references/gotchas.md`, `references/evidence.md`
- `scripts/firecrawl_guard.py` for offline worst-case estimates (`estimate`) and the free balance check (`balance`)
- `scripts/test_helper.py` for offline regressions pinned to billed amounts
