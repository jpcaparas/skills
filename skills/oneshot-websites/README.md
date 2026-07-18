# Oneshot Websites

Production skill for launching autonomous one-shot website experiments through fresh isolated subagents.

## What It Adds

- A catalogue seeded with 100 prompts spanning interfaces, games, simulations, tools, motion, data, stories, commerce, science, and maps, each with a plain title and scan-friendly description
- A catalogue-first no-argument response, grouped by namespace with a one-line explanation for every option
- Silent visual and interaction-first guidance for crafting each finished brief without leaking generic boilerplate into `PROMPT.md`
- One fresh lead subagent per experiment, with recursive delegation allowed
- No skill-imposed time, stack, dependency, workflow, or source-project constraints
- Collision-free model/harness/experiment namespaces
- Faithful one- or two-paragraph prompt crafting for catalogue and custom briefs, with only the finished brief preserved in `PROMPT.md`
- A conservative Cloudflare/Vercel Drop-ready `artifact/` with one root `index.html` entrypoint and any supporting asset tree the experience needs
- A coordinator-owned receipt-and-commit inventory outside each worker run, with crash recovery and an explicit path-isolation trust boundary
- Provenance-aware indexing and validation

## Key Files

- `SKILL.md` - authoritative instructions
- `assets/prompt-catalogue.json` - canonical prompt catalogue
- `references/execution-protocol.md` - delegation and namespace contract
- `agents/oneshot-lead.md` - isolated lead role
- `scripts/list_prompts.py` - catalogue browser
- `scripts/validate_catalog.py` - generated artifact checker
