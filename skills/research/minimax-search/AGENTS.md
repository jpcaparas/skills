# minimax-search

**Version 1.0.0**  
JP Caparas  
October 2026

This wrapper exists for repository presentation. The authoritative agent instructions live in `SKILL.md`.

Read `SKILL.md` first. Then load the specific file in `references/` that matches the user's task:

- `references/api.md` for the request contract, response fields, error codes, quota, and rate limits
- `references/patterns.md` for helper, `curl`, and `jq` workflows
- `references/configuration.md` for key type, region, and prerequisites
- `references/gotchas.md` for surprising output and failure handling
- `references/evidence.md` for what was measured live and what remains untested

`scripts/validate.py`, `scripts/test_skill.py`, and `scripts/test_helper.py` stay offline and never use an ambient API key.
