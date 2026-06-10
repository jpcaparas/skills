# scaffold-github-copilot-hooks

Repository-agnostic skill for auditing a project and scaffolding GitHub Copilot hooks with a repeatable `.github/hooks/copilot-hooks.json` managed layout.

## What It Adds

- live-doc verification against the official GitHub Copilot hooks docs before scaffolding
- a deep project audit before any hook plan is chosen
- a deterministic bash-first managed hook scaffold that covers every documented Copilot hook event
- correct Copilot output-decision behavior for `preToolUse`, `permissionRequest`, `agentStop`, and `postToolUseFailure`
- reusable repo-owned script delegation for logic that should also run from Devin, Codex, OpenCode, Git hooks, CI, or a shell
- additive and overhaul refresh modes for projects that already have hooks
- generated `.github/copilot/hooks/README.md` output so the target project has a readable event map

## Key Files

- `SKILL.md` for the authoritative workflow
- `references/hook-events.md` for the current event catalog, matcher rules, decisions, and exit codes
- `references/scaffold-layout.md` for the generated target structure
- `references/reusable-scripts.md` for cross-agent and CI-friendly script placement
- `scripts/verify_docs.py` to compare live docs with the static hook contract
- `scripts/audit_project.sh` to profile a real project
- `scripts/scaffold_hooks.sh` to build or refresh the managed hook scaffold
- `assets/hook-events.json` for the current static event manifest used by the deterministic scaffold
