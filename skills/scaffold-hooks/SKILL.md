---
name: scaffold-hooks
description: "Universal /scaffold-hooks scaffolder for Claude Code, Codex, GitHub Copilot, Devin CLI, and OpenCode hooks — together or individually. Audits a project, detects existing hook surfaces, refreshes only those harnesses by default, and wires selected `.claude`, `.codex`, `.github`, `.devin`, and `.opencode` configs into repo-owned `hooks/` scaffolding. Do NOT use for Git hooks or Husky."
---

# Universal Agent Hook Scaffold

Scaffold or migrate agent lifecycle hooks so every selected harness points at repo-owned hook scaffolding. This is the single hooks scaffolder: the former `scaffold-cc-hooks`, `scaffold-codex-hooks`, `scaffold-github-copilot-hooks`, `scaffold-devin-hooks`, and `scaffold-opencode-hooks` skills are retired and live here as internal harness components under `harnesses/<name>/`.

## Decision Tree

1. If the user says `/scaffold-hooks`, hooks, lifecycle hooks, hook migration, or names any of Claude Code, Codex, GitHub Copilot, Devin CLI, or OpenCode hooks, use this skill.
2. If the user names harnesses, pass exactly those harnesses with `--harnesses <list>`. A single-harness request is just `--harnesses <name>`.
3. If the user gives no target path, use the current workspace or repository root as the target project.
4. If the user gives no harness preference, inspect the target project. When any supported hook surface or managed scaffold state exists, run the universal script without `--harnesses` so it refreshes exactly the detected harnesses. Do not add new harnesses unless the user explicitly asks.
5. If no supported hook surface exists, ask which harnesses to scaffold. Default to all supported harnesses (`claude`, `codex`, `copilot`, `devin`, `opencode`) for a new scaffold.
6. If existing configs point at `.claude/hooks/generated`, `.codex/hooks/generated`, or `.devin/hooks/generated`, treat the work as a migration: strip those managed command entries, scaffold `hooks/`, and remove only legacy managed folders that contain a manifest.
7. If the project has custom hooks outside managed roots, preserve them unless the user explicitly asks for removal.

## Harness Selection

Selection order is deterministic:

1. Explicit `--harnesses` from the user.
2. A custom universal plan's `harnesses` list, when present.
3. Detected existing hook surfaces or managed scaffold state in the target repo.
4. The default all-supported set only when none of the above exists.

Detected surfaces include current managed manifests, legacy generated manifests, shared adapters under `hooks/`, and harness config files that already contain hook entries. If any harness is detected, do not expand to other harnesses without explicit user direction.

- `claude` — Claude Code, `.claude/settings.json`
- `codex` — Codex CLI, `.codex/hooks.json` (requires the hooks feature flag; see `harnesses/codex/references/feature-flag.md`)
- `copilot` — GitHub Copilot (cloud agent + CLI), `.github/hooks/copilot-hooks.json` with generated events under `.github/copilot/hooks/generated/`
- `devin` — Devin CLI, `.devin/hooks.v1.json`
- `opencode` — OpenCode, `opencode.json` plus `.opencode/hook/hooks.md` through `opencode-froggy`

Pass explicit additions as `--harnesses claude,codex,copilot,devin,opencode` (or a subset). A bare run on a repo that already has hooks is a refresh, not an expansion.

## Quick Reference

| Task | Command |
| --- | --- |
| Refresh detected existing harnesses, or scaffold all in a clean repo | `scripts/scaffold_all_hooks.sh --project /path/to/project` |
| Preview without writes | `scripts/scaffold_all_hooks.sh --project /path/to/project --dry-run` |
| Use a project-specific universal plan | `scripts/scaffold_all_hooks.sh --project /path/to/project --plan /path/to/scaffold-hooks.json` |
| Scaffold only selected harnesses | `scripts/scaffold_all_hooks.sh --project /path/to/project --harnesses claude,codex` |
| Refresh harness adapters while preserving shared event scripts | `scripts/scaffold_all_hooks.sh --project /path/to/project --mode overhaul` |
| Audit a target repo for one harness | `harnesses/<name>/scripts/audit_project.sh /path/to/project` |
| Validate a harness component | `python3 harnesses/<name>/scripts/validate.py harnesses/<name>` |
| Run a harness test suite | `python3 harnesses/<name>/scripts/test_skill.py harnesses/<name>` |

## Standard Workflow

1. Inspect the target project first:
   - existing `.claude/settings*.json`
   - `.codex/hooks.json` and `.codex/config.toml`
   - `.devin/hooks.v1.json` and `.devin/config*.json`
   - `opencode.json`, `.opencode/hook/hooks.md`, old `.opencode/plugins/.managed/`, and any custom `.opencode/plugins/`
   - `.github/hooks/copilot-hooks.json` and `.github/copilot/hooks/generated/`
   - existing `hooks/` tree and repo-owned validation scripts under `scripts/`
2. Confirm the harness set only when creating a new scaffold or adding harnesses. For a bare invocation on a repo with existing hook surfaces, refresh the detected set only.
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
.opencode/
  hook/
    hooks.md
    README.md
    .managed/
      manifest.json
      plan.snapshot.json
opencode.json
```

Harness config files stay in their documented locations:

- Claude: `.claude/settings.json`
- Codex: `.codex/hooks.json`
- Devin: `.devin/hooks.v1.json`
- OpenCode: `opencode.json` loads `opencode-froggy`; Froggy reads `.opencode/hook/hooks.md`
- GitHub Copilot: `.github/hooks/copilot-hooks.json` with generated events under `.github/copilot/hooks/generated/` (self-contained because the Copilot cloud agent reads everything from the repo)

## Plan Shape

Use `templates/hook-plan.example.json` as the source of truth for the universal plan schema. The top-level plan controls shared behavior:

- `mode`: `additive` or `overhaul`
- `hooks_root`: normally `hooks`
- `cleanup_legacy`: remove old managed generated folders only when they contain a manifest
- `harnesses`: subset of `claude`, `codex`, `copilot`, `devin`, `opencode`; use this only when intentionally choosing or expanding the harness set
- `plans`: per-harness plan objects passed to the harness components

Read `references/plan-format.md` before adding project-specific scripts or commands.

## Collision Policy

This skill is conservative:

- Strip old managed generated-root commands before appending new `hooks/<event>/<harness>.sh` commands.
- Preserve non-managed custom hooks in the same config files.
- Preserve existing `hooks/<event>/script.sh` files so shared project behavior is not rewritten by another harness.
- In `overhaul` mode, delete only selected harness adapters/state under `hooks/`, then call the harness components in additive mode for shell harnesses.
- For OpenCode, preserve unmanaged `.opencode/plugins/` files but migrate scaffold-owned plugin output to `opencode-froggy` and `.opencode/hook/hooks.md`.

Read `references/collision-policy.md` before changing merge behavior.

## Harness Components

Each supported harness is a self-contained component under `harnesses/<name>/` with its own `PLAYBOOK.md`, scaffolding scripts, event manifest, templates, references, validator, and test suite:

- `harnesses/claude/` owns Claude Code event semantics and `.claude/settings.json` merging.
- `harnesses/codex/` owns Codex event semantics, feature-flag handling, and `.codex/hooks.json` merging.
- `harnesses/devin/` owns Devin event semantics and `.devin/hooks.v1.json` merging.
- `harnesses/opencode/` owns OpenCode Froggy configuration, `opencode.json` plugin merging, and cleanup of prior scaffold-owned local plugin artifacts.
- `harnesses/copilot/` owns GitHub Copilot event semantics and `.github/hooks/copilot-hooks.json` merging for the cloud agent and Copilot CLI.

When an event name, matcher, output contract, or feature flag changes, update the harness component first (manifest, references, scripts, tests), then the universal orchestration. Read `references/harness-composition.md` when changing the composition order or adding a harness.

## Protocol Output Hygiene

Treat stdout as part of the harness protocol, not a scratch log. For JSON-output hooks, stdout is reserved for the final protocol JSON payload; successful no-op paths should stay quiet unless the event contract explicitly allows stdout. Send diagnostics, debug text, filenames, and human-readable failure details to stderr unless the harness requires them on stdout.

Helper and predicate functions must be silent by default and return exit status only. Use quiet checks such as `grep -q` / `grep -Eq`, or redirect stdout to `/dev/null`; do not use filename probes like `grep ... | head -1` unless the output is captured and cannot leak to hook stdout. Known regression: `hook_has_code_changes` must remain an exit-status-only predicate.

Validate generated JSON-output hooks for zero stdout on success/no-op paths, parseable JSON with no prefix or suffix on blocking paths, and no filenames/debug/status lines leaking from shared helpers.

## Gotchas

1. Do not pass `overhaul` directly to the shell harness scaffolders from a universal run. They would rewrite shared `script.sh` files. The universal script performs harness cleanup first, then calls them additively.
2. OpenCode now uses `opencode-froggy` as the plugin layer. Do not recreate the old generated `.opencode/plugins/*.ts` lifecycle adapter unless the user explicitly asks for custom plugin code.
3. Legacy generated folders should be deleted only when they contain a managed manifest. Otherwise they may be user-owned files with an unfortunate path name.
4. A clean-looking config can still collide if old generated commands remain. Always scan final configs for `.claude/hooks/generated`, `.codex/hooks/generated`, and `.devin/hooks/generated`.
5. Keep project policy in repo-owned scripts such as `./scripts/agent-stop-checks.sh`; hook adapters should translate protocol, not duplicate validation logic. Generated shell Stop adapters default to `run_on_code_changes: true` and use detected source/config extensions so expensive checks do not run on clean turns.
6. Copilot does not write adapters into the shared `hooks/` tree. Its generated events stay under `.github/copilot/hooks/generated/` because the Copilot cloud agent only reads files committed to the repository; keep shared policy in repo-owned `scripts/` that both layers call.
7. Shared scripts that emit session context should use the Claude/Codex/Devin `hookSpecificOutput.additionalContext` JSON shape. Devin strictly parses non-empty stdout as Claude-format JSON and silently drops plain text; Claude Code also accepts the shared JSON shape, so do not special-case Claude for `SessionStart`. See `references/harness-composition.md` for details.
8. Treat exit codes and output streams as separate contracts. Exit code controls success, failure, or blocking; stderr is for diagnostics and failure reasons, not successful status messages. Successful routine skips should write to stdout only when the harness protocol allows it, or stay quiet.
9. Froggy's `isMainSession` condition handles main-session filtering for OpenCode hooks; use it on session lifecycle hooks that should skip child/subagent sessions.
10. Managed manifests record scaffold skill provenance, plan/template hashes, selected harnesses, detected harnesses, selection source, and managed file hashes. Re-runs should use those snapshots to refresh unchanged managed adapters while preserving user-modified files.
11. A bare `/scaffold-hooks` invocation is conservative. If any supported hook surface is detected, refresh only that detected set; do not expand to other harnesses unless the user explicitly asks.

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
