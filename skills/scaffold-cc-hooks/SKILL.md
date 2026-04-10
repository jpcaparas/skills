---
name: scaffold-cc-hooks
description: "Scaffold Claude Code hooks into a real project after auditing the project structure in detail. Use when a user wants Claude Code hook setup, hook refactors, full hook-event scaffolding, or managed updates to existing .claude hooks. This skill verifies the live official Claude Code hook docs first, audits the target repo, then generates a bash-first hook scaffold with a hooks README, repeatable merge behavior, and coverage for every current hook event. Trigger on: Claude Code hooks, scaffold hooks, hook events, update hooks, hook architecture, .claude/settings.json. Do NOT use for generic Git hooks, Husky-only setup, or non-Claude agents."
compatibility: "Requires: bash, jq, git, rg"
metadata:
  version: "1.0.0"
  short-description: "Project-aware Claude Code hook scaffolder"
  openclaw:
    category: "development"
    requires:
      bins: [bash, jq, git, rg]
references:
  - project-analysis
  - hook-events
  - scaffold-layout
  - merge-strategy
  - gotchas
---

# scaffold-cc-hooks

Audit the target project first, then scaffold Claude Code hooks with a deterministic bash-first layout.

## Decision Tree

What is the user asking for?

- New Claude Code hooks in a project with no hook setup yet:
  Run live docs verification, audit the project, choose a hook plan, then scaffold.
- Existing `.claude/settings*.json` or `.claude/hooks/` files:
  Audit what already exists, choose `additive` or `overhaul`, then regenerate only the managed hook layer.
- Existing hooks plus possible Claude Code feature drift:
  Verify the live official hook event list before writing files. If the docs changed, update the scaffold inputs first.
- Explanation only, not implementation:
  Read `references/hook-events.md` and `references/scaffold-layout.md`, then answer without scaffolding.

## Quick Reference

| Task | Action |
|------|--------|
| Verify the current official hook model | Read the live official docs at `https://code.claude.com/docs/en/hooks` and `https://code.claude.com/docs/en/hooks-guide`, then compare them to `assets/hook-events.json` |
| Audit a target repo | Run `scripts/audit_project.sh /path/to/project` |
| Understand the event catalog | Read `references/hook-events.md` |
| Decide additive vs overhaul | Read `references/merge-strategy.md` |
| Generate or refresh the managed hook scaffold | Run `scripts/scaffold_hooks.sh --project /path/to/project --plan /path/to/plan.json --mode additive|overhaul` |
| Merge generated hooks into settings | Let `scripts/scaffold_hooks.sh` call `scripts/merge_settings.sh`, or run the merge script directly |
| Regenerate the hooks README in a target project | Run `scripts/render_hooks_readme.sh --project /path/to/project --plan /path/to/plan.json` |

## Non-Negotiable Workflow

1. Verify the live official Claude Code hook docs before planning any scaffold.
2. Compare the live event list, hook type support, and async rules with `assets/hook-events.json`.
3. Audit the target project in detail before deciding which events to enable.
4. Inspect any existing `.claude/settings.json`, `.claude/settings.local.json`, `.claude/hooks/`, `CLAUDE.md`, `.claude/rules/`, and related automation files before choosing a merge mode.
5. Produce or update a concrete hook plan JSON. Keep the scaffold deterministic by putting project-specific judgment into the plan, not into the scaffold script.
6. Scaffold every current hook event as a commented bash stub under the managed hook root, even if the event stays disabled in settings.
7. Wire only the enabled events into the chosen settings file so the project does not pay runtime cost for inactive stubs.
8. Regenerate `.claude/hooks/README.md` so the project always has a readable event map.

## Live Docs First

The official Claude Code docs are the source of truth:

- `https://code.claude.com/docs/en/hooks`
- `https://code.claude.com/docs/en/hooks-guide`

Use the two reading.sh articles only as secondary material for practical patterns and trade-off language:

- `https://reading.sh/claude-code-hooks-a-bookmarkable-guide-to-git-automation-11b4516adc5d`
- `https://reading.sh/claude-code-async-hooks-what-they-are-and-when-to-use-them-61b21cd71aad`

If the official docs and the secondary articles disagree, follow the official docs and update the local references.

## Project Analysis Rules

Before choosing any hook structure, inspect:

- repo root and workspace shape
- languages and package managers
- build, test, lint, and format entry points
- monorepo tools like Turborepo, Nx, pnpm workspaces, Bun workspaces, or custom task runners
- existing Claude Code settings, rules, hooks, plugins, and skills
- existing Git hooks, Husky, Lefthook, or CI gates
- sensitive paths like `.env`, secrets, migrations, lockfiles, generated code, and infra directories
- environment reload needs such as `direnv`, `.envrc`, or per-directory tooling

Run `scripts/audit_project.sh` first, then read `references/project-analysis.md` when you need the full checklist.

## Deterministic vs Project-Specific Work

Keep these parts deterministic:

- managed hook root path
- event stub filenames
- generated settings fragment shape
- merge behavior for previously managed hooks
- hooks README generation
- event manifest coverage for every current official hook event

Allow these parts to stay project-specific:

- which events are enabled
- event matchers
- sync vs async choice
- `if` filters on tool events
- timeouts
- the actual logic inside enabled event scripts
- whether the refresh is `additive` or `overhaul`

## Repeat-Run Rules

When the skill is invoked again against a project:

- Re-run live docs verification before assuming the event set is unchanged.
- Re-audit the project before assuming the current hook plan still fits.
- Preserve non-managed hooks by default.
- Treat previously generated hooks under the managed root as replaceable in `overhaul` mode.
- Treat previously generated hooks as append-only in `additive` mode unless a missing event or stale README requires a refresh.
- If new official hook events exist, add new stubs and README entries even if the project keeps them disabled.

## Scaffold Rules

- Generate bash scripts, not Python, for the project hook runtime.
- Comment the generated bash stubs in plain language.
- Use `$CLAUDE_PROJECT_DIR` in generated command paths.
- Default to a managed root of `.claude/hooks/generated` unless the project already has a stronger convention.
- Default to `.claude/settings.json` when the hook setup should be shared. Use `.claude/settings.local.json` only when the project needs machine-local behavior or already uses that pattern.
- Keep one managed script per event so the event map stays obvious.
- Keep the merged settings deterministic: remove only previously managed handlers, never unrelated custom hooks.

## Reading Guide

| Need | Read |
|------|------|
| Full audit checklist and what to inspect first | `references/project-analysis.md` |
| Current official event list and support matrix | `references/hook-events.md` |
| Managed folder layout and plan file shape | `references/scaffold-layout.md` |
| Additive versus overhaul behavior | `references/merge-strategy.md` |
| Async, `if`, shell, and settings pitfalls | `references/gotchas.md` |

## Operational Scripts

- `scripts/audit_project.sh` builds a project profile from real repo signals.
- `scripts/scaffold_hooks.sh` renders the managed hook tree, manifest, README, and settings fragment.
- `scripts/merge_settings.sh` preserves non-managed hooks while replacing previously managed handlers.
- `scripts/render_hooks_readme.sh` rebuilds `.claude/hooks/README.md` from the manifest and the current plan.

## Gotchas

1. `async` only applies to command hooks, and async hooks cannot block or steer Claude after the triggering action is already done.
2. The `if` field only works on tool events and requires Claude Code v2.1.85 or later.
3. `Stop` hooks can loop forever unless you honor `stop_hook_active`.
4. Hook shells are non-interactive. Shell profile noise can break JSON output.
5. `PermissionRequest` does not fire in non-interactive `-p` mode.

