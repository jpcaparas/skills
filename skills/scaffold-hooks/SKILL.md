---
name: scaffold-hooks
description: "Universal /scaffold-hooks migration for Claude Code, Codex, Devin CLI, and OpenCode. Audits a project and rewires `.claude`, `.codex`, `.devin`, and `.opencode` configs into one repo-owned `hooks/` ports-and-adapters tree. Do NOT use for Git hooks or one-harness-only requests."
---

# Universal Agent Hook Scaffold

Scaffold or migrate Claude Code, Codex, Devin CLI, and OpenCode hooks so every harness points at one shared `hooks/` directory.

## Decision Tree

1. If the user says `/scaffold-hooks`, universal hooks, all agent harnesses, or cross-harness hook migration, use this skill.
2. If the user asks for only Claude, Codex, Devin, or OpenCode by name and does not want the other harnesses touched, use the dedicated skill: `{{ skill:scaffold-cc-hooks }}`, `{{ skill:scaffold-codex-hooks }}`, `{{ skill:scaffold-devin-hooks }}`, or `{{ skill:scaffold-opencode-hooks }}`.
3. If existing configs point at `.claude/hooks/generated`, `.codex/hooks/generated`, or `.devin/hooks/generated`, treat the work as a migration: strip those managed command entries, scaffold `hooks/`, and remove only legacy managed folders that contain a manifest.
4. If the project has custom hooks outside managed roots, preserve them unless the user explicitly asks for removal.
5. If the user wants GitHub Copilot hooks too, keep that separate unless they explicitly broaden this skill; Copilot has a different repository/cloud-agent surface.

## Quick Reference

| Task | Command |
| --- | --- |
| Scaffold all four harnesses with the default shared plan | `scripts/scaffold_all_hooks.sh --project /path/to/project` |
| Preview without writes | `scripts/scaffold_all_hooks.sh --project /path/to/project --dry-run` |
| Use a project-specific universal plan | `scripts/scaffold_all_hooks.sh --project /path/to/project --plan /path/to/scaffold-hooks.json` |
| Scaffold only selected harnesses | `scripts/scaffold_all_hooks.sh --project /path/to/project --harnesses claude,codex` |
| Refresh harness adapters while preserving shared event scripts | `scripts/scaffold_all_hooks.sh --project /path/to/project --mode overhaul` |

## Standard Workflow

1. Inspect the target project first:
   - existing `.claude/settings*.json`
   - `.codex/hooks.json` and `.codex/config.toml`
   - `.devin/hooks.v1.json` and `.devin/config*.json`
   - `.opencode/plugins/`, `opencode.json`, and `.opencode/package.json`
   - existing `hooks/` tree and repo-owned validation scripts under `scripts/`
2. Verify the dedicated harness docs through the component skills before making event-surface changes. This skill composes the current dedicated scaffolders rather than duplicating their event manifests.
3. Start from `templates/hook-plan.example.json` unless the project already has a clearer plan.
4. Run `scripts/scaffold_all_hooks.sh` with `--dry-run`, then without `--dry-run`.
5. Review `hooks/README.md`, the harness config files, and the selected adapters.
6. Run the project’s normal validation.

## Output Shape

The target project should end up with this pattern:

```text
hooks/
  README.md
  lib/
    agent-hook-runtime.sh
    claude.sh
    codex.sh
    devin.sh
  .state/
    scaffold-hooks/
    claude/
    codex/
    devin/
  stop/
    script.sh
    claude.sh
    claude.json
    codex.sh
    codex.json
    devin.sh
    devin.json
  opencode-session-created/
    script.sh
    opencode.sh
  opencode-session-idle/
    script.sh
    opencode.sh
```

Harness config files stay in their documented locations:

- Claude: `.claude/settings.json`
- Codex: `.codex/hooks.json`
- Devin: `.devin/hooks.v1.json`
- OpenCode: `.opencode/plugins/*.ts` plus optional `opencode.json` entries for npm plugins

## Plan Shape

Use `templates/hook-plan.example.json` as the source of truth for the universal plan schema. The top-level plan controls shared behavior:

- `mode`: `additive` or `overhaul`
- `hooks_root`: normally `hooks`
- `cleanup_legacy`: remove old managed generated folders only when they contain a manifest
- `harnesses`: subset of `claude`, `codex`, `devin`, `opencode`
- `plans`: per-harness plan objects passed to the dedicated scaffolders

Read `references/plan-format.md` before adding project-specific scripts or commands.

## Collision Policy

This skill is conservative:

- Strip old managed generated-root commands before appending new `hooks/<event>/<harness>.sh` commands.
- Preserve non-managed custom hooks in the same config files.
- Preserve existing `hooks/<event>/script.sh` files so shared project behavior is not rewritten by another harness.
- In `overhaul` mode, delete only selected harness adapters/state under `hooks/`, then call the dedicated scaffolders in additive mode for shell harnesses.
- Keep OpenCode’s `.opencode/plugins/` layer because OpenCode loads plugins from there; make those plugins thin adapters into `hooks/opencode-*`.

Read `references/collision-policy.md` before changing merge behavior.

## Component Skills

This skill deliberately delegates harness details:

- `{{ skill:scaffold-cc-hooks }}` owns Claude Code event semantics and `.claude/settings.json` merging.
- `{{ skill:scaffold-codex-hooks }}` owns Codex event semantics, feature-flag handling, and `.codex/hooks.json` merging.
- `{{ skill:scaffold-devin-hooks }}` owns Devin event semantics and `.devin/hooks.v1.json` merging.
- `{{ skill:scaffold-opencode-hooks }}` owns OpenCode plugin generation and config/package merging.

Read `references/harness-composition.md` when changing the composition order or adding a harness.

## Gotchas

1. Do not pass `overhaul` directly to the shell harness scaffolders from a universal run. They would rewrite shared `script.sh` files. The universal script performs harness cleanup first, then calls them additively.
2. OpenCode cannot be represented only by JSON config. Its documented extension point is plugin files, so `.opencode/plugins/*.ts` remains a required adapter layer.
3. Legacy generated folders should be deleted only when they contain a managed manifest. Otherwise they may be user-owned files with an unfortunate path name.
4. A clean-looking config can still collide if old generated commands remain. Always scan final configs for `.claude/hooks/generated`, `.codex/hooks/generated`, and `.devin/hooks/generated`.
5. Keep project policy in repo-owned scripts such as `./scripts/agent-stop-checks.sh`; hook adapters should translate protocol, not duplicate validation logic.

## Progressive Maintainer Drift Check

When this skill changes, verify the dedicated harness skills first and then run this skill’s tests. Do not update the universal orchestration from memory; the dedicated scaffolders are the event-contract source of truth.
