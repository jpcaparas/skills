# scaffold-cc-hooks

Repository-agnostic skill for auditing a project and scaffolding Claude Code hooks with a repeatable managed layout.

## What It Adds

- live-doc verification against the official Claude Code hooks docs before scaffolding
- a deep project audit before any hook plan is chosen
- an early workspace-trust diagnostic path for the common "hooks show up but never fire" failure mode
- a deterministic bash-first managed hook scaffold that covers every current hook event
- reusable repo-owned script delegation for logic that should also run from Codex, OpenCode, Git hooks, CI, or a shell
- additive and overhaul refresh modes for projects that already have hooks
- generated `.claude/hooks/README.md` output so the target project has a readable event map

## Key Files

- `SKILL.md` for the authoritative workflow
- `references/project-analysis.md` for the audit checklist
- `references/hook-events.md` for the current event catalog and support matrix
- `references/scaffold-layout.md` for the generated target structure
- `references/reusable-scripts.md` for cross-agent and CI-friendly script placement
- `references/merge-strategy.md` for repeat-run behavior
- `references/gotchas.md` for trust and other failure modes that look like hook bugs
- `scripts/audit_project.sh` to profile a real project
- `scripts/check_workspace_trust.sh` to inspect or enable Claude Code workspace trust for an exact project path
- `scripts/scaffold_hooks.sh` to build or refresh the managed hook scaffold
- `scripts/merge_settings.sh` to merge generated hooks into Claude settings without trampling unrelated hooks
- `scripts/render_hooks_readme.sh` to rebuild the hook-folder README in the target project
- `assets/hook-events.json` for the current static event manifest used by the deterministic scaffold
