---
name: scaffold-codex-hooks
description: "Scaffold Codex hooks into a real project after auditing the repo, verifying the live official docs and schemas, inspecting the effective `codex_hooks` feature flag, and enabling it in project or user config if needed. Use when a user wants Codex hooks, `.codex/hooks.json`, managed Codex hook refreshes, repo-local lifecycle Bash hooks, or help with `SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, or `Stop`. Trigger on: Codex hooks, hooks.json, codex_hooks, .codex/config.toml, feature flag, managed hook scaffold. Do NOT use for Claude Code hooks, `.claude/settings.json`, Husky-only setups, or non-Codex agents."
compatibility: "Requires: codex CLI with the under-development `codex_hooks` feature available, plus bash, jq, git, rg, and python3. Hooks are currently disabled on Windows."
metadata:
  version: "1.0.0"
  short-description: "Project-aware Codex hooks scaffolder"
  openclaw:
    category: "development"
    requires:
      bins: [codex, bash, jq, git, rg, python3]
references:
  - project-analysis
  - feature-flag
  - hook-events
  - scaffold-layout
  - merge-strategy
  - gotchas
---

# scaffold-codex-hooks

Audit the target project first, then scaffold Codex hooks with a deterministic managed layout around the current official hook model.

## Decision Tree

What is the user asking for?

- New project-local Codex hooks in a repo with no hook setup yet:
  Verify the live official docs and schemas, audit the repo, inspect the effective feature flag, enable it if needed, then scaffold.
- Existing `.codex/hooks.json`, `.codex/config.toml`, or `.codex/hooks/` files:
  Audit what exists first, choose `additive` or `overhaul`, then refresh only the managed hook layer.
- Hooks that exist on disk but never seem to affect Codex:
  Inspect the effective `codex_hooks` feature first. If it is still off, enable it deliberately. If it is on, remember that repo-local `.codex/config.toml` only loads in trusted projects, then debug `hooks.json`.
- Explanation only, not implementation:
  Read `references/hook-events.md`, `references/feature-flag.md`, and `references/scaffold-layout.md`, then answer without scaffolding.

## Quick Reference

| Task | Action |
|------|--------|
| Verify the current official Codex hook model | Read `https://developers.openai.com/codex/hooks`, `https://developers.openai.com/codex/config-basic`, and the generated schemas listed in `assets/hook-events.json` |
| Audit a target repo | Run `scripts/audit_project.sh /path/to/project` |
| Inspect the effective `codex_hooks` feature | Run `python3 scripts/check_hooks_feature.py --project /path/to/project --json` |
| Enable hooks in project config | Run `python3 scripts/check_hooks_feature.py --project /path/to/project --enable --scope project` |
| Enable hooks in user config | Run `python3 scripts/check_hooks_feature.py --project /path/to/project --enable --scope user` |
| Understand the current event catalog | Read `references/hook-events.md` |
| Decide additive vs overhaul | Read `references/merge-strategy.md` |
| Generate or refresh the managed hook scaffold | Run `scripts/scaffold_hooks.sh --project /path/to/project --plan /path/to/plan.json --mode additive|overhaul --ensure-feature project|user|off` |
| Merge generated handlers into `.codex/hooks.json` | Let `scripts/scaffold_hooks.sh` call `scripts/merge_hooks_json.sh`, or run the merge script directly |
| Regenerate the hooks README in a target project | Run `scripts/render_hooks_readme.sh --project /path/to/project --plan /path/to/plan.json` |

## Non-Negotiable Workflow

1. Verify the live official Codex hook docs before planning any scaffold.
2. Compare the live docs, current schemas, and `assets/hook-events.json` before assuming the event set or output contract is unchanged.
3. Audit the target project in detail before deciding which events to enable or which commands to run.
4. Inspect the effective `codex_hooks` feature in the target project before treating any repo-local `hooks.json` as active.
5. If the feature is off, enable it deliberately in the right scope:
   - default to project scope for shared repo scaffolds
   - use user scope for personal/global hooks or when the repo should not commit `.codex/config.toml`
6. Inspect any existing `.codex/config.toml`, `.codex/hooks.json`, `.codex/hooks/`, `AGENTS.md`, `README*`, and other automation files before choosing a merge mode.
7. Produce or update a concrete hook plan JSON. Keep the scaffold deterministic by putting project-specific judgment into the plan, not into the scaffold script.
8. Scaffold every current official event as a commented bash stub under the managed hook root, even if that event stays disabled in `hooks.json`.
9. Wire only the enabled events into `.codex/hooks.json` so inactive stubs stay cheap.
10. Regenerate `.codex/hooks/README.md` so the target project always has a readable event map.
11. If hooks still appear inactive after a real scaffold, re-check the effective feature state and remember that project config files only load in trusted projects.

## Feature First Heuristic

Check `codex_hooks` early whenever any of these signals appear:

- the user asks to scaffold Codex hooks into a repo
- `.codex/hooks.json` exists, but nothing seems to happen
- the user is unsure whether the feature flag is on
- a repo-local `.codex/config.toml` exists, but the effective feature still looks off

Use this flow:

1. Canonicalize the target project path first.
2. Run `python3 scripts/check_hooks_feature.py --project /path/to/project --json`.
3. If the effective status is off, enable the feature deliberately:
   - `--scope project` for shared repo-local setups
   - `--scope user` for personal/global setups
4. Re-run the inspection after enabling.
5. Only then spend time debugging `hooks.json`, matcher choices, or hook script logic.

## Live Docs First

The official Codex docs are the source of truth:

- `https://developers.openai.com/codex/hooks`
- `https://developers.openai.com/codex/config-basic`
- `https://developers.openai.com/codex/config-reference`

For exact wire formats and current parser behavior, also verify:

- `https://github.com/openai/codex/tree/main/codex-rs/hooks/schema/generated`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/engine/discovery.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/engine/config.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/events/common.rs`

Use the article at `https://reading.sh/codex-hooks-just-gave-you-back-complete-control-over-your-code-57d044bcae1b` as secondary material for practical patterns, not as the source of truth. Early hook writeups drifted as the feature evolved.

## Project Analysis Rules

Before choosing any hook structure, inspect:

- repo root and workspace shape
- whether the project already has `.codex/config.toml`, `.codex/hooks.json`, or `.codex/hooks/`
- languages and package managers
- build, test, lint, format, and validation entry points
- monorepo tools like Turborepo, Nx, pnpm workspaces, Bun workspaces, Cargo workspaces, or custom task runners
- existing AI instructions such as `AGENTS.md`, project rules, or repo automation docs
- existing Git hooks, Husky, Lefthook, or CI gates
- sensitive paths like `.env`, secrets, lockfiles, generated code, migrations, and infra directories
- whether the hook setup should be shareable in repo config or kept user-local

Run `scripts/audit_project.sh` first, then read `references/project-analysis.md` when you need the full checklist.

## Deterministic vs Project-Specific Work

Keep these parts deterministic:

- managed hook root path
- event stub filenames
- generated `hooks.generated.json` shape
- merge behavior for previously managed hooks
- hooks README generation
- event manifest coverage for every current official Codex hook event
- feature-flag inspection and reporting

Allow these parts to stay project-specific:

- which events are enabled
- matcher regexes for supported events
- timeouts and status messages
- whether feature enablement belongs in project or user config
- the actual logic inside enabled event scripts
- whether the refresh is `additive` or `overhaul`

## Repeat-Run Rules

When the skill is invoked again against a project:

- Re-verify the live docs and schemas before assuming the event set is unchanged.
- Re-audit the project before assuming the current hook plan still fits.
- Re-check the effective feature state before assuming repo-local hooks are active.
- Preserve non-managed hooks by default.
- Treat previously generated hooks under the managed root as replaceable in `overhaul` mode.
- Treat previously generated hooks as append-only in `additive` mode unless the managed layer or README is stale.
- If the official event set or parser rules changed, update the scaffold inputs first.

## Scaffold Rules

- Generate bash scripts, not Python, for the managed runtime hook stubs.
- Comment the generated bash stubs with the event-specific input and output contract.
- Default to a managed root of `.codex/hooks/generated`.
- Default to a hooks file target of `.codex/hooks.json`.
- Default to enabling `codex_hooks` in `.codex/config.toml` for shared repo scaffolds.
- Use `~/.codex/config.toml` only when the hook setup should stay personal or machine-local.
- Keep one managed script per official event so the event map stays obvious.
- Keep the merged `hooks.json` deterministic: remove only previously managed handlers, never unrelated custom hooks.
- Never assume `async`, `prompt`, or `agent` hooks work today. The current runtime skips them.
- Never pretend `PreToolUse` or `PostToolUse` can currently see `Write`, `MCP`, `WebSearch`, or every shell invocation. Today the useful matcher value is `Bash`.
- Treat `Stop` carefully. For that event, `decision: "block"` means "continue Codex with this new prompt", not "reject the turn".

## Reading Guide

| Need | Read |
|------|------|
| Full audit checklist and planning questions | `references/project-analysis.md` |
| How to inspect and enable `codex_hooks` safely | `references/feature-flag.md` |
| Current official event list, matcher support, and output semantics | `references/hook-events.md` |
| Managed folder layout and plan file shape | `references/scaffold-layout.md` |
| Additive versus overhaul behavior | `references/merge-strategy.md` |
| Runtime limits, docs drift, and fail-open traps | `references/gotchas.md` |

## Operational Scripts

- `scripts/audit_project.sh` builds a project profile from real repo signals.
- `scripts/check_hooks_feature.py` inspects or enables `codex_hooks` in user or project config.
- `scripts/scaffold_hooks.sh` renders the managed hook tree, manifest, fragment, README, and feature setup.
- `scripts/merge_hooks_json.sh` preserves non-managed handlers while replacing previously managed ones.
- `scripts/render_hooks_readme.sh` rebuilds `.codex/hooks/README.md` from the manifest and current plan.
- `scripts/validate.py` checks structure, frontmatter, manifest integrity, and cross-references.
- `scripts/test_skill.py` runs lightweight validation plus temp-project integration checks.

## Gotchas

1. `PreToolUse` and `PostToolUse` are Bash-only today. A regex like `Edit|Write` is valid, but it will not match anything useful in current Codex.
2. `matcher` is ignored for `UserPromptSubmit` and `Stop`. Do not design logic that depends on those matchers.
3. `async`, `prompt`, and `agent` parse in config shapes, but the current runtime skips them with warnings.
4. Multiple matching command hooks for the same event run concurrently. One hook cannot stop another matching hook from starting.
5. `PostToolUse` cannot undo command side effects. At best it can replace the feedback Codex sees next.
6. `Stop` with `decision: "block"` continues Codex with a new prompt. It does not reject the turn.
7. Repo-local `.codex/config.toml` only loads in trusted projects. If you enable the feature in project scope but the project is not trusted, the effective feature can still look off.
8. Early blog posts described smaller event sets. Re-check the official docs and schemas every time you scaffold for real.
