# scaffold-codex-hooks

Repository-agnostic skill for auditing a project and scaffolding Codex hooks with a repeatable managed layout.

## What It Adds

- live-doc and schema verification against the current official Codex hooks docs before scaffolding
- a deep project audit before any hook plan is chosen
- deterministic inspection and optional enablement of the `codex_hooks` feature flag
- a managed `.codex/hooks.json` workflow that preserves unrelated custom hooks
- one generated bash stub per current official Codex hook event
- additive and overhaul refresh modes for projects that already have Codex hooks
- a generated `.codex/hooks/README.md` so the target project has a readable event map

## Key Files

- `SKILL.md` for the authoritative workflow
- `references/project-analysis.md` for the audit checklist
- `references/feature-flag.md` for feature-scope and trust guidance
- `references/hook-events.md` for the current event catalog and output semantics
- `references/scaffold-layout.md` for the generated target structure
- `references/merge-strategy.md` for repeat-run behavior
- `references/gotchas.md` for runtime limits and docs drift traps
- `scripts/audit_project.sh` to profile a real project
- `scripts/check_hooks_feature.py` to inspect or enable `codex_hooks`
- `scripts/scaffold_hooks.sh` to build or refresh the managed hook scaffold
- `scripts/merge_hooks_json.sh` to merge generated handlers into `.codex/hooks.json`
- `scripts/render_hooks_readme.sh` to rebuild the hook-folder README in the target project
- `assets/hook-events.json` for the current static event manifest used by the deterministic scaffold
