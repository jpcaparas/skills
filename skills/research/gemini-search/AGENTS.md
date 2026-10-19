# gemini-search

**Version 1.0.0**  
JP Caparas  
October 2026

This wrapper exists for repository presentation. The authoritative agent instructions live in `SKILL.md`.

Read `SKILL.md` first. Then load the specific file in `references/` that matches the user's task:

- `references/api.md` for endpoints, tools, response fields, models, prices, billing, and rate limits
- `references/patterns.md` for helper, `curl`, and `jq` workflows, list batching, and structured output
- `references/gotchas.md` for silent failures and ignored parameters
- `references/expensive-routes.md` for Deep Research, Max, Pro, and Argon, and how to ask permission
- `references/evidence.md` for what was measured live and what remains untested

`scripts/validate.py`, `scripts/test_skill.py`, and `scripts/test_helper.py` stay offline and never use an ambient API key.
