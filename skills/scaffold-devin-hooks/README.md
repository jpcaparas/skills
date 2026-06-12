# scaffold-devin-hooks

Repository-agnostic skill for auditing a project and scaffolding Devin CLI hooks with a repeatable `.devin/hooks.v1.json` managed layout.

## What It Adds

- live-doc verification against the official Devin hooks docs before scaffolding
- a deep project audit before any hook plan is chosen
- a deterministic bash-first managed hook scaffold that covers every documented Devin lifecycle event
- exit-code-2 blocking behavior for gates that must deny an action
- reusable repo-owned script delegation for logic that should also run from Codex, OpenCode, Git hooks, CI, or a shell
- additive and overhaul refresh modes for projects that already have hooks
- `hooks/README.md` output so the target project has a readable shared event and adapter map

## Key Files

- `SKILL.md` for the authoritative workflow
- `references/project-analysis.md` for the audit checklist
- `references/hook-events.md` for the current event catalog, matcher rules, and exit codes
- `references/scaffold-layout.md` for the managed target structure
- `references/reusable-scripts.md` for cross-agent and CI-friendly script placement
- `references/merge-strategy.md` for repeat-run behavior
- `references/gotchas.md` for failure modes that look like hook bugs
- `scripts/verify_docs.py` to compare live docs with the static hook contract
- `scripts/audit_project.sh` to profile a real project
- `scripts/scaffold_hooks.sh` to build or refresh the managed hook scaffold
- `scripts/merge_hooks_file.sh` to merge managed hooks into `.devin/hooks.v1.json` without trampling unrelated hooks
- `scripts/render_hooks_readme.sh` to rebuild the hook-folder README in the target project
- `assets/hook-events.json` for the current static event manifest used by the deterministic scaffold
