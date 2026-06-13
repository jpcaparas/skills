---
name: scaffold-hooks
description: "Universal /scaffold-hooks scaffolder for Claude Code, Codex, GitHub Copilot, Devin CLI, and OpenCode hooks — together or individually. Audits a project, asks which harnesses to target (default all), and wires `.claude`, `.codex`, `.github`, `.devin`, and `.opencode` hook configs into repo-owned scaffolding around one shared `hooks/` ports-and-adapters tree. Do NOT use for Git hooks or Husky."
---

# Universal Agent Hook Scaffold

Scaffold or migrate agent lifecycle hooks so every selected harness points at repo-owned hook scaffolding. This is the single hooks scaffolder: the former `scaffold-cc-hooks`, `scaffold-codex-hooks`, `scaffold-github-copilot-hooks`, `scaffold-devin-hooks`, and `scaffold-opencode-hooks` skills are retired and live here as internal harness components under `harnesses/<name>/`.

## Decision Tree

1. If the user says `/scaffold-hooks`, hooks, lifecycle hooks, hook migration, or names any of Claude Code, Codex, GitHub Copilot, Devin CLI, or OpenCode hooks, use this skill.
2. Ask which harnesses to scaffold unless the user already said so. Default to **all supported harnesses** (`claude`, `codex`, `copilot`, `devin`, `opencode`). A single-harness request is just `--harnesses <name>`.
3. If existing configs point at `.claude/hooks/generated`, `.codex/hooks/generated`, or `.devin/hooks/generated`, treat the work as a migration: strip those managed command entries, scaffold `hooks/`, and remove only legacy managed folders that contain a manifest.
4. If the project has custom hooks outside managed roots, preserve them unless the user explicitly asks for removal.

## Harness Selection

Before scaffolding, confirm the harness set with the user (multi-select, default all):

- `claude` — Claude Code, `.claude/settings.json`
- `codex` — Codex CLI, `.codex/hooks.json` (requires the hooks feature flag; see `harnesses/codex/references/feature-flag.md`)
- `copilot` — GitHub Copilot (cloud agent + CLI), `.github/hooks/copilot-hooks.json` with generated events under `.github/copilot/hooks/generated/`
- `devin` — Devin CLI, `.devin/hooks.v1.json`
- `opencode` — OpenCode, `.opencode/plugins/*.ts`

Pass the answer as `--harnesses claude,codex,copilot,devin,opencode` (or a subset). When the user gives no preference, scaffold all supported harnesses.

## Quick Reference

| Task | Command |
| --- | --- |
| Scaffold all harnesses with the default shared plan | `scripts/scaffold_all_hooks.sh --project /path/to/project` |
| Preview without writes | `scripts/scaffold_all_hooks.sh --project /path/to/project --dry-run` |
| Use a project-specific universal plan | `scripts/scaffold_all_hooks.sh --project /path/to/project --plan /path/to/scaffold-hooks.json` |
| Scaffold only selected harnesses | `scripts/scaffold_all_hooks.sh --project /path/to/project --harnesses claude,codex` |
| Refresh harness adapters while preserving shared event scripts | `scripts/scaffold_all_hooks.sh --project /path/to/project --mode overhaul` |
| Audit a target repo for one harness | `harnesses/<name>/scripts/audit_project.sh /path/to/project` |
| Validate a harness component | `python3 harnesses/<name>/scripts/validate.py harnesses/<name>` |
| Run a harness test suite | `python3 harnesses/<name>/scripts/test_skill.py harnesses/<name>` |

## Standard Workflow

1. Confirm the harness set with the user (default all supported harnesses).
2. Inspect the target project first:
   - existing `.claude/settings*.json`
   - `.codex/hooks.json` and `.codex/config.toml`
   - `.devin/hooks.v1.json` and `.devin/config*.json`
   - `.opencode/plugins/`, `opencode.json`, and `.opencode/package.json`
   - `.github/hooks/copilot-hooks.json` and `.github/copilot/hooks/generated/`
   - existing `hooks/` tree and repo-owned validation scripts under `scripts/`
3. Verify the live official harness docs before making event-surface changes. Each harness component records its verified contract in `harnesses/<name>/assets/hook-events.json` and its workflow in `harnesses/<name>/PLAYBOOK.md`.
4. Start from `templates/hook-plan.example.json` unless the project already has a clearer plan.
5. Run `scripts/scaffold_all_hooks.sh` with `--dry-run`, then without `--dry-run`.
6. Review `hooks/README.md`, `hooks/.state/scaffold-hooks/manifest.json`, the harness config files, and the selected adapters.
7. Run the project's normal validation.

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
      manifest.json
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
- GitHub Copilot: `.github/hooks/copilot-hooks.json` with generated events under `.github/copilot/hooks/generated/` (self-contained because the Copilot cloud agent reads everything from the repo)

## Plan Shape

Use `templates/hook-plan.example.json` as the source of truth for the universal plan schema. The top-level plan controls shared behavior:

- `mode`: `additive` or `overhaul`
- `hooks_root`: normally `hooks`
- `cleanup_legacy`: remove old managed generated folders only when they contain a manifest
- `harnesses`: subset of `claude`, `codex`, `copilot`, `devin`, `opencode`
- `plans`: per-harness plan objects passed to the harness components

Read `references/plan-format.md` before adding project-specific scripts or commands.

## Collision Policy

This skill is conservative:

- Strip old managed generated-root commands before appending new `hooks/<event>/<harness>.sh` commands.
- Preserve non-managed custom hooks in the same config files.
- Preserve existing `hooks/<event>/script.sh` files so shared project behavior is not rewritten by another harness.
- In `overhaul` mode, delete only selected harness adapters/state under `hooks/`, then call the harness components in additive mode for shell harnesses.
- Keep OpenCode's `.opencode/plugins/` layer because OpenCode loads plugins from there; make those plugins thin adapters into `hooks/opencode-*`.

Read `references/collision-policy.md` before changing merge behavior.

## Harness Components

Each supported harness is a self-contained component under `harnesses/<name>/` with its own `PLAYBOOK.md`, scaffolding scripts, event manifest, templates, references, validator, and test suite:

- `harnesses/claude/` owns Claude Code event semantics and `.claude/settings.json` merging.
- `harnesses/codex/` owns Codex event semantics, feature-flag handling, and `.codex/hooks.json` merging.
- `harnesses/devin/` owns Devin event semantics and `.devin/hooks.v1.json` merging.
- `harnesses/opencode/` owns OpenCode plugin generation and config/package merging.
- `harnesses/copilot/` owns GitHub Copilot event semantics and `.github/hooks/copilot-hooks.json` merging for the cloud agent and Copilot CLI.

When an event name, matcher, output contract, or feature flag changes, update the harness component first (manifest, references, scripts, tests), then the universal orchestration. Read `references/harness-composition.md` when changing the composition order or adding a harness.

## Gotchas

1. Do not pass `overhaul` directly to the shell harness scaffolders from a universal run. They would rewrite shared `script.sh` files. The universal script performs harness cleanup first, then calls them additively.
2. OpenCode cannot be represented only by JSON config. Its documented extension point is plugin files, so `.opencode/plugins/*.ts` remains a required adapter layer.
3. Legacy generated folders should be deleted only when they contain a managed manifest. Otherwise they may be user-owned files with an unfortunate path name.
4. A clean-looking config can still collide if old generated commands remain. Always scan final configs for `.claude/hooks/generated`, `.codex/hooks/generated`, and `.devin/hooks/generated`.
5. Keep project policy in repo-owned scripts such as `./scripts/agent-stop-checks.sh`; hook adapters should translate protocol, not duplicate validation logic.
6. Copilot does not write adapters into the shared `hooks/` tree. Its generated events stay under `.github/copilot/hooks/generated/` because the Copilot cloud agent only reads files committed to the repository; keep shared policy in repo-owned `scripts/` that both layers call.
7. Shared scripts that emit context must branch per harness for the stdout protocol. Devin strictly parses non-empty stdout as Claude-format JSON and silently drops plain text; Claude Code accepts plain text on `SessionStart`. See `references/harness-composition.md` for details.
8. OpenCode publishes normal session lifecycle events for child/subagent sessions. The OpenCode lifecycle plugin must cache child IDs from `session.created` events with `info.parentID` and skip context or stop-style work for those IDs.
9. Managed manifests record scaffold skill provenance, plan/template hashes, and managed file hashes. Re-runs should use those snapshots to refresh unchanged managed adapters while preserving user-modified files.

## Hook Visibility Matrix

Harness TUIs differ in whether hook activity is visible. Set expectations during scaffolding so users do not mistake silence for failure:

| Harness | Renders hook runs in TUI | Verify hooks via |
|---------|--------------------------|------------------|
| Claude Code | Partially (errors, verbose mode) | `/hooks`, transcript |
| Codex CLI | Yes ("Running SessionStart hook", hook context inline) | visible inline |
| Devin CLI | No (silent even on success; `systemMessage` not rendered as of v2026.5.26-8) | `/hooks`, CLI logs, transcript JSON, ask the agent |
| OpenCode | Plugin-defined | plugin logs |
| GitHub Copilot | Cloud agent: session logs; CLI: varies | session logs, `.github/copilot/hooks/generated/` output |

## Progressive Maintainer Drift Check

When this skill changes, live-fetch the official hook docs for every affected harness on the day of the edit and compare them with `harnesses/<name>/assets/hook-events.json`. Update the harness component first (manifest, references, generators, templates, validators, tests), then the universal orchestration. Do not update this skill from memory; the per-harness manifests are the event-contract source of truth. Each `harnesses/<name>/PLAYBOOK.md` carries the detailed drift checklist for its harness.
