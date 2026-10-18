# deepseek-search

**Version 1.0.0**  
JP Caparas  
October 2026

This wrapper exists for repository presentation. The authoritative agent instructions live in `SKILL.md`.

Read `SKILL.md` first. Then load the specific file in `references/` that matches the user's task:

- `references/api.md` for request and response fields, validation rules, errors and retries, billing, rate limits, and the balance endpoint
- `references/patterns.md` for helper, `curl`, and `jq` workflows, fan-out, multi-site coverage, and spend estimates
- `references/gotchas.md` for surprising output and failure handling
- `references/model-search.md` for letting a DeepSeek model run web search itself
- `references/evidence.md` for what was measured live and what remains untested

`scripts/validate.py`, `scripts/test_skill.py`, and `scripts/test_helper.py` stay offline and never use an ambient API key.
