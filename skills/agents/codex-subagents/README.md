# codex-subagents

Installable Codex CLI/App skill for using Codex subagents deliberately: explicit authorization, bounded delegation, disjoint write ownership, model-neutral custom-agent guidance, and main-thread synthesis.

## Install

```bash
npx skills add jpcaparas/skills --skill codex-subagents
```

## Includes

- `SKILL.md` as the canonical delegation workflow
- `references/delegation-policy.md` for spawn and skip gates
- `references/codex-mechanics.md` for Codex subagent configuration and custom agents
- `references/patterns.md` for reusable delegation prompts
- `scripts/detect_codex_surface.py` as a conservative local preflight

This skill is Codex CLI/App specific and should stay inert in other harnesses.
