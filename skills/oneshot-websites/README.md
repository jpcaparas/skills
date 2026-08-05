# Oneshot Websites

Production skill for launching autonomous one-shot website experiments through fresh isolated subagents.

## What It Adds

- A catalogue seeded with 100 prompts spanning interfaces, games, simulations, tools, motion, data, stories, commerce, science, and maps, each with a plain title and scan-friendly description
- A catalogue-first no-argument response, grouped by namespace with a one-line explanation for every option
- Silent visual and interaction-first guidance for crafting each finished brief without leaking generic boilerplate into `PROMPT.md`
- A universal subject-adapted completion mandate in every finished prompt: no shortcuts, no cookie-cutter approximations, no skill-imposed token budget, and full interaction depth
- One fresh lead subagent per experiment, with recursive delegation allowed
- Explicit outer fan-out for multiple leads, workspaces, and same-prompt replicas
- A lead-owned quality gauntlet with concrete bars, fresh read-only critics, real-artifact comparison, highest-leverage fixes, and evidence-based stopping
- Coupling-aware delegation that reserves parallel work for independently improvable concerns and smooths the integrated artifact before final review
- A preserved `.tmp/` inside every unique run, with best-effort temp routing inherited by descendants and kept out of prompts and deployable artifacts
- No skill-imposed time, stack, dependency, workflow, or source-project constraints
- Evidence-gated WebAssembly selection: reuse proven compiled cores when justified, benchmark uncertain hot paths, and keep ordinary web work in the web stack
- Flat `timestamp-experiment-slug` run directories with atomic `--02` collision suffixes
- Faithful, fully developed prompt crafting for catalogue and custom briefs, with the complete refined brief preserved in `PROMPT.md`
- End-to-end UTF-8 preservation for intended punctuation, emoji, and non-Latin scripts, with fail-fast detection of recognizable mojibake
- A conservative Cloudflare/Vercel Drop-ready `artifact/` with one root `index.html` entrypoint and any supporting asset tree the experience needs
- A local-only default: Drop compatibility never authorizes Vercel, Cloudflare, ChatGPT, GitHub, or other remote writes; explicit action-and-destination permission is required and retained by the coordinator
- A coordinator-owned receipt-and-commit inventory outside each worker run, with crash recovery and an explicit path-isolation trust boundary
- Provenance-aware indexing and validation

## Key Files

- `SKILL.md` - authoritative instructions
- `assets/prompt-catalogue.json` - canonical prompt catalogue
- `references/execution-protocol.md` - delegation and flat run-layout contract
- `references/wasm-selection.md` - conditional WASM decision gate, measurements, artifact rules, and sample scenarios
- `agents/oneshot-lead.md` - isolated lead role
- `agents/oneshot-critic.md` - fresh read-only artifact critic
- `scripts/list_prompts.py` - catalogue browser
- `scripts/validate_catalog.py` - generated artifact checker
