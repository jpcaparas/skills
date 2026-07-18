# Oneshot Websites

Production skill for launching autonomous one-shot website experiments through fresh isolated subagents.

## What It Adds

- A catalogue seeded with 100 prompts spanning interfaces, games, simulations, tools, motion, data, stories, commerce, science, and maps
- One fresh lead subagent per experiment, with recursive delegation allowed
- No skill-imposed time, stack, dependency, workflow, or source-project constraints
- Collision-free model/harness/experiment namespaces
- A conservative Cloudflare/Vercel Drop-ready `artifact/` containing the original `PROMPT.md` and one root `index.html`
- A coordinator-owned receipt-and-commit inventory outside each worker run, with crash recovery and an explicit path-isolation trust boundary
- Provenance-aware indexing and validation

## Key Files

- `SKILL.md` - authoritative instructions
- `assets/prompt-catalogue.json` - canonical prompt catalogue
- `references/execution-protocol.md` - delegation and namespace contract
- `agents/oneshot-lead.md` - isolated lead role
- `scripts/list_prompts.py` - catalogue browser
- `scripts/validate_catalog.py` - generated artifact checker
