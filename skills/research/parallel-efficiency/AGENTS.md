# parallel-efficiency

**Version 1.0.0**  
JP Caparas  
October 2026

This wrapper exists for repository presentation. The authoritative agent instructions live in `SKILL.md`.

Read `SKILL.md` first. Then load the specific file in `references/` that matches the task:

- `references/pricing.md` for every product, endpoint, price, default, rate limit, and free tier with sources
- `references/recipes.md` for the cheapest REST, CLI, and MCP request shapes per job
- `references/account-guards.md` for balance checks, notify-only spend limits, auto-reload, and monitors
- `references/gotchas.md` for surprising charges and recovery
- `references/evidence.md` for what was checked and what remains untested

`scripts/validate.py`, `scripts/test_skill.py`, and `scripts/test_helper.py` stay offline and never use an ambient API key.
