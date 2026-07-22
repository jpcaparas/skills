# Oneshot Websites

Production skill for launching autonomous one-shot website experiments through fresh isolated subagents.

## What It Adds

- A catalogue seeded with 100 prompts spanning interfaces, games, simulations, tools, motion, data, stories, commerce, science, and maps, each with a plain title and scan-friendly description
- A catalogue-first no-argument response, grouped by namespace with a one-line explanation for every option
- Silent visual and interaction-first guidance for crafting each finished brief without leaking generic boilerplate into `PROMPT.md`
- A universal subject-adapted completion mandate in every finished prompt: no shortcuts, no cookie-cutter approximations, no skill-imposed token budget, and full interaction depth
- One fresh lead subagent per experiment, with recursive delegation allowed
- A preserved `.tmp/` inside every unique run, with best-effort temp routing inherited by descendants and kept out of prompts and deployable artifacts
- No skill-imposed time, stack, dependency, workflow, or source-project constraints
- Flat, local-time run directories with atomic same-second collision suffixes
- Faithful, fully developed prompt crafting for catalogue and custom briefs, with the complete refined brief preserved in `PROMPT.md`
- End-to-end UTF-8 preservation for intended punctuation, emoji, and non-Latin scripts, with fail-fast detection of recognizable mojibake
- A conservative Cloudflare/Vercel Drop-ready `artifact/` with one root `index.html` entrypoint and any supporting asset tree the experience needs
- A coordinator-owned receipt-and-commit inventory outside each worker run, with crash recovery and an explicit path-isolation trust boundary
- Provenance-aware indexing and validation

## Key Files

- `SKILL.md` - authoritative instructions
- `assets/prompt-catalogue.json` - canonical prompt catalogue
- `references/execution-protocol.md` - delegation and flat run-layout contract
- `agents/oneshot-lead.md` - isolated lead role
- `scripts/list_prompts.py` - catalogue browser
- `scripts/validate_catalog.py` - generated artifact checker
