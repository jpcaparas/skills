# synthetic-search

**Version 2.0.0**  
JP Caparas  
October 2026

This wrapper exists for repository presentation. The authoritative agent instructions live in `SKILL.md`.

Read `SKILL.md` first. Then load the specific file in `references/` that matches the user's task:

- `references/api.md` for the request contract, response fields, errors, and quota semantics
- `references/patterns.md` for helper, `curl`, and `jq` workflows
- `references/configuration.md` for setup and prerequisite checks
- `references/gotchas.md` for surprising output and failure handling
- `references/evidence.md` for what was measured live and what remains untested

`scripts/validate.py`, `scripts/test_skill.py`, and `scripts/test_helper.py` stay offline and never use an ambient API key. `scripts/probe_synthetic_search.py` calls the live API and spends hourly search quota.
