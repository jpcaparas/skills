# scaffold-codex-hooks

Repository-agnostic skill for auditing a project and scaffolding Codex hooks with a repeatable managed layout.

## What It Adds

- live-doc, schema, and runtime-source verification against current Codex hook behavior before scaffolding
- a deep project audit before any hook plan is chosen
- deterministic inspection and optional enablement of the canonical `hooks` feature flag
- review/trust guidance for non-managed command hooks after scaffold changes
- a managed `.codex/hooks.json` workflow that preserves unrelated custom hooks
- one managed bash stub per current source-backed Codex hook event
- reusable repo-owned script delegation for logic that should also run from Claude Code, OpenCode, Git hooks, CI, or a shell
- additive and overhaul refresh modes for projects that already have Codex hooks
- a `hooks/README.md` so the target project has a readable shared event and adapter map

## Key Files

- `SKILL.md` for the authoritative workflow
- `references/project-analysis.md` for the audit checklist
- `references/feature-flag.md` for feature-scope and trust guidance
- `references/hook-events.md` for the current event catalog and output semantics
- `references/scaffold-layout.md` for the managed target structure
- `references/reusable-scripts.md` for cross-agent and CI-friendly script placement
- `references/merge-strategy.md` for repeat-run behavior
- `references/gotchas.md` for runtime limits and docs drift traps
- `scripts/audit_project.sh` to profile a real project
- `scripts/check_hooks_feature.py` to inspect or enable `hooks`
- `scripts/scaffold_hooks.sh` to build or refresh the managed hook scaffold
- `scripts/merge_hooks_json.sh` to merge managed handlers into `.codex/hooks.json`
- `scripts/render_hooks_readme.sh` to rebuild the hook-folder README in the target project
- `assets/hook-events.json` for the current static event manifest used by the deterministic scaffold
