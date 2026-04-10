# scaffold-cc-hooks

Repository-agnostic skill for auditing a project and scaffolding Claude Code hooks with a repeatable managed layout.

## What It Adds

- live-doc verification against the official Claude Code hooks docs before scaffolding
- a deep project audit before any hook plan is chosen
- a deterministic bash-first managed hook scaffold that covers every current hook event
- additive and overhaul refresh modes for projects that already have hooks
- generated `.claude/hooks/README.md` output so the target project has a readable event map

## Key Files

- `SKILL.md` for the authoritative workflow
- `references/project-analysis.md` for the audit checklist
- `references/hook-events.md` for the current event catalog and support matrix
- `references/scaffold-layout.md` for the generated target structure
- `references/merge-strategy.md` for repeat-run behavior
- `scripts/audit_project.sh` to profile a real project
- `scripts/scaffold_hooks.sh` to build or refresh the managed hook scaffold
- `scripts/merge_settings.sh` to merge generated hooks into Claude settings without trampling unrelated hooks
- `scripts/render_hooks_readme.sh` to rebuild the hook-folder README in the target project
- `assets/hook-events.json` for the current static event manifest used by the deterministic scaffold

