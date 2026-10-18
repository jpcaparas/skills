# nanobanana

**Version 1.0.0**  
JP Caparas  
October 2026

This wrapper exists for repository presentation. The authoritative agent instructions live in `SKILL.md`.

Read `SKILL.md` first. Then load the specific file in `references/` that matches the task:

- `references/prompting.md` for prompt structure, text, references, edits, and templates
- `references/workflows.md` for helper recipes, batch, transparency, and post-processing
- `references/api.md` for raw Interactions and generateContent contracts, sizes, pricing, and errors
- `references/gotchas.md` for surprising behaviour and recovery
- `references/evidence.md` for what was measured live and what remains untested

The skill is pinned to `gemini-nano-banana-2.1`. `scripts/validate.py`, `scripts/test_skill.py`, and `scripts/test_helper.py` stay offline and never use an ambient API key.
