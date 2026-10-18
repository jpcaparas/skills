# firecrawl-efficiency

**Version 1.0.0**  
JP Caparas  
October 2026

This wrapper exists for repository presentation. The authoritative agent instructions live in `SKILL.md`.

Read `SKILL.md` first. Then load the specific file in `references/` that matches the task:

- `references/pricing.md` for every endpoint, modifier, plan, and rate limit with sources
- `references/recipes.md` for the cheapest REST and MCP request shapes per job
- `references/account-guards.md` for pay-as-you-go, spend limits, monitors, and usage endpoints
- `references/gotchas.md` for surprising charges and recovery
- `references/evidence.md` for what was measured live and what remains untested

The skill never calls `/agent` or `/extract`. `scripts/validate.py`, `scripts/test_skill.py`, and `scripts/test_helper.py` stay offline and never use an ambient API key.
