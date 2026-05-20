---
name: scaffold-opencode-hooks
description: "Scaffold OpenCode hooks by generating TypeScript-only OpenCode plugins into a real project after auditing the repo, verifying the live official plugin docs, and inspecting config precedence. Defaults to a minimal lifecycle/action plugin with visible TUI toasts, repo-owned scripts, and one controlled automatic follow-up; generates broad hook-surface catalogs only when requested. Trigger on OpenCode hooks, OpenCode plugins, `.opencode/plugins`, TypeScript lifecycle plugins, `opencode.json`, `tool.execute.before`, `tool.execute.after`, `session.idle`, `shell.env`, custom tools, or post-turn checks. Do NOT use for Codex hooks, Claude Code hooks, JavaScript-only plugin scaffolds, or generic npm package publishing with no OpenCode runtime."
compatibility: "Requires: bash, jq, git, rg, bun"
metadata:
  version: "1.0.0"
  short-description: "Project-aware OpenCode hook and plugin scaffolder"
  openclaw:
    category: "development"
    requires:
      bins: [bash, jq, git, rg, bun]
references:
  - project-analysis
  - config-layering
  - hook-events
  - plugin-patterns
  - scaffold-layout
  - merge-strategy
  - gotchas
---

# scaffold-opencode-hooks

Audit the target project first, then scaffold OpenCode hooks as managed OpenCode plugins with deterministic file generation and repeatable config merges.

## Decision Tree

What is the user asking for?

- New OpenCode hooks in a repo with no existing plugin setup:
  Verify the live docs, audit the repo, inspect existing OpenCode config state, choose project-local or global scope, then scaffold the minimal lifecycle/action plugin unless the user asks for a broad hook catalog.
- Mirroring existing agent lifecycle hooks or running post-action automation:
  Generate one live TypeScript plugin that calls repo-owned scripts, shows TUI toasts for meaningful background work, and allows one controlled automatic repair/follow-up prompt.
- Existing `.opencode/plugins/`, `.opencode/package.json`, or `opencode.json` / `opencode.jsonc` files:
  Audit what already exists, choose `additive` or `overhaul`, then refresh only the managed plugin layer.
- Existing plugins that should be shareable in the repo:
  Default to project-local `.opencode/plugins/` and only touch `opencode.json` when npm plugin entries are part of the plan.
- Personal or machine-local hooks across many repos:
  Target `~/.config/opencode/plugins/` and `~/.config/opencode/opencode.json` instead of the project tree.
- OpenCode plugin troubleshooting:
  Inspect config precedence, plugin directories, config-dir dependencies, and cache or disable flows before rewriting plugin logic.
- Explanation only, not implementation:
  Read `references/hook-events.md`, `references/config-layering.md`, `references/plugin-patterns.md`, and `references/scaffold-layout.md`, then answer without scaffolding.

## Quick Reference

| Task | Action |
|------|--------|
| Verify the current official OpenCode plugin model | Read `https://opencode.ai/docs/plugins/`, `https://opencode.ai/docs/config/`, `https://opencode.ai/docs/sdk`, `https://opencode.ai/docs/custom-tools`, and compare them with `assets/hook-events.json` |
| Audit a target repo | Run `scripts/audit_project.sh /path/to/project` |
| Inspect project-vs-global OpenCode setup | Run `bun scripts/check_plugin_setup.ts --project /path/to/project --json` |
| Merge npm plugin names into an OpenCode config file | Run `bun scripts/merge_opencode_config.ts --config-file /path/to/opencode.json --plugins plugin-a plugin-b` |
| Merge config-dir dependencies for local plugins | Run `bun scripts/merge_package_json.ts --package-file /path/to/.opencode/package.json --dependencies-json '{"@opencode-ai/plugin":"^1.15.5"}'` |
| Generate the minimal lifecycle/action scaffold | Start from `templates/hook-plan.example.json`, then run `bash scripts/scaffold_hooks.sh --project /path/to/project --plan /path/to/plan.json --mode additive|overhaul` |
| Generate a broad hook-surface scaffold | Start from `templates/hook-plan.broad.example.json` and set `surface_catalog: true` |
| Regenerate the plugin README in a target project | Run `bash scripts/render_hooks_readme.sh --project /path/to/project --plan /path/to/plan.json` |

## Non-Negotiable Workflow

1. Verify the live official OpenCode plugin docs before planning any scaffold.
2. Compare the live docs, config guidance, and SDK examples with `assets/hook-events.json` before assuming the surface catalog is unchanged.
3. Audit the target project in detail before deciding scope, deployment style, module format, or which plugin patterns to enable.
4. Inspect any existing `opencode.json`, `opencode.jsonc`, `.opencode/plugins/`, `.opencode/package.json`, `AGENTS.md`, and other automation files before choosing a merge mode.
5. Choose scope deliberately:
   - default to project-local when the hooks should travel with the repo
   - default to global only when the behavior should stay personal or cross-project
6. Produce or update a concrete plan JSON. Keep the scaffold deterministic by putting project-specific judgment into the plan, not into the scaffold script.
7. Prefer the minimal lifecycle/action plugin for lifecycle mirroring, post-action automation, validation, formatter repair, generated-file drift, dependency setup, or policy checks.
8. Scaffold reference stubs for every current official OpenCode hook surface only when the user asks for a broad scaffold or the plan sets `surface_catalog: true`.
9. Generate only the enabled managed plugin modules into the active plugin load path so dormant stubs do not become runtime plugins by accident.
10. Merge config plugin arrays and config-dir package dependencies deterministically, without deleting unrelated user-owned entries. Do not create config-dir package files when no runtime dependency is needed.
11. Regenerate the plugin README so the target project has a concise map of active behavior. For minimal scaffolds, do not print a full hook-surface catalog.

## Config Layer First Heuristic

Inspect OpenCode setup early whenever any of these signals appear:

- the user wants OpenCode hooks scaffolded into a repo
- `.opencode/plugins/` already exists
- `opencode.json` or `opencode.jsonc` already contains a `plugin` array
- the user wants personal hooks that should apply across multiple repos
- plugins exist on disk but OpenCode behaves strangely, crashes, or ignores the intended workflow

Use this flow:

1. Canonicalize the target project path first.
2. Run `bun scripts/check_plugin_setup.ts --project /path/to/project --json`.
3. Decide scope from the existing OpenCode footprint:
   - existing repo-local `.opencode/` setup or a shared repo use case -> project
   - personal or cross-repo behavior -> global
4. Decide deployment style:
   - custom logic you own -> local plugin files
   - shared third-party packages plus local custom logic -> hybrid
5. Only then edit plugin files, config arrays, or config-dir dependencies.

## Live Docs First

The official OpenCode docs are the source of truth:

- `https://opencode.ai/docs/plugins/`
- `https://opencode.ai/docs/config/`
- `https://opencode.ai/docs/sdk`
- `https://opencode.ai/docs/custom-tools`
- `https://opencode.ai/docs/troubleshooting`

Use the article at `https://blog.devgenius.io/opencode-auto-lint-your-ai-agents-code-with-a-post-turn-biome-hook-7158d75c63db?postPublishedType=repub` as secondary practical guidance for post-turn validation patterns, not as the source of truth for paths, load order, or lifecycle semantics.

If the official docs and the article disagree, follow the official docs and update the local references.

## Project Analysis Rules

Before choosing any OpenCode hook structure, inspect:

- repo root and workspace shape
- whether the project already has `.opencode/plugins/`, `.opencode/package.json`, `opencode.json`, or `opencode.jsonc`
- languages and package managers
- build, test, lint, format, and validation entry points
- monorepo tools like Turborepo, Nx, pnpm workspaces, Bun workspaces, Cargo workspaces, or custom task runners
- existing AI instructions such as `AGENTS.md`, repo rules, or automation docs
- sensitive paths like `.env`, secrets, lockfiles, generated code, migrations, and infra directories
- whether the hook setup should be shareable in-repo or remain machine-local
- whether local plugin logic needs config-dir dependencies, Bun shell calls, or SDK-driven feedback loops

Run `scripts/audit_project.sh` first, then read `references/project-analysis.md` when you need the full checklist.

## Deterministic vs Project-Specific Work

Keep these parts deterministic:

- the managed plugin filename prefix
- the managed state directory layout
- optional broad stub coverage for every current official hook surface
- config plugin-array merges
- config-dir package dependency merges only when dependencies are actually needed
- README generation
- additive vs overhaul semantics for previously managed plugin files

Allow these parts to stay project-specific:

- which live plugin modules are enabled
- whether the scaffold targets project or global scope
- whether the generated modules are TypeScript
- whether npm plugin entries should be merged into config
- the actual plugin logic inside enabled modules
- cooldowns, tool lists, validation commands, and feedback prompts
- which repo-owned scripts implement session context, validation, formatting, dependency setup, or policy checks
- which meaningful background actions deserve visible TUI feedback
- whether the refresh is `additive` or `overhaul`

## Repeat-Run Rules

When the skill is invoked again against a project:

- Re-verify the live docs before assuming the surface set is unchanged.
- Re-audit the project before assuming the current plugin plan still fits.
- Preserve unrelated user plugins by default.
- Preserve unrelated `plugin` array entries in `opencode.json` or `opencode.jsonc`.
- Preserve unrelated config-dir dependencies in `.opencode/package.json`.
- Treat previously generated plugin files listed in the managed manifest as replaceable in `overhaul` mode.
- Treat previously generated files as append-only in `additive` mode unless the user explicitly asks for a reset.
- If the official docs add or remove hook surfaces, update the manifest inputs first.

## Scaffold Rules

- Generate TypeScript plugin modules only. Do not create `.js`, `.mjs`, `.cjs`, `.jsx`, or `.tsx` plugin files from this managed scaffold.
- Keep live managed plugin modules directly in the active plugin directory so OpenCode definitely loads them.
- Generate one live lifecycle/action plugin for minimal lifecycle mirroring or post-action automation. Keep full hook-surface stubs under a non-loading managed state directory only for broad scaffolds.
- Default to project-local `.opencode/plugins/` for shared repo scaffolds.
- Default to global `~/.config/opencode/plugins/` only when the behavior should remain personal or cross-project.
- Create or normalize the config-dir `package.json` only when live TypeScript plugin modules import external runtime dependencies.
- Only add `@opencode-ai/plugin` when the generated scaffold actually needs the `tool()` helper or typed imports.
- Keep logging and user-visible feedback separate: use `client.app.log()` for structured diagnostics and `client.tui.showToast()` for what the user should see.
- Add a best-effort `showToast(client, variant, message)` helper to generated plugins. Wrap it in `try/catch`; toast failures must never break hook behavior. Use `info`, `success`, `warning`, and `error`.
- Show an `info` toast when meaningful background work starts, a `success` toast when it completes, and a `warning` or `error` toast when intervention is needed. Apply this to `session.idle`, `tool.execute.after`, `command.executed`, `file.edited`, `installation.updated`, `session.error`, and custom cross-event workflows when they do real work.
- For automatic repair or follow-up, allow one `client.session.prompt()` without `noReply` on the first failure. Track `inFlight`, `repairPromptSent`, and `persistentFailureReported`; use `noReply: true` for persistent failure notices so the plugin cannot loop indefinitely.
- Call repo-owned scripts for project-specific behavior instead of hard-coding build, test, lint, or policy commands in plugin bodies. Prefer reusable project conventions such as a session-context script and a shared validation script under the target repo's scripts directory.
- Use `tool.execute.before` for prevention, `tool.execute.after` for observation, and `event` for cross-event coordination like `session.idle`.
- Treat `experimental.session.compacting` as opt-in and experimental. Do not make core safety logic depend on it.
- Never assume local helper `.js` or `.ts` files under the plugin directory are inert. Anything with a runtime module extension may load as a plugin, so this scaffold writes only enabled `.ts` plugin modules into the active plugin directory.

## Reading Guide

| Need | Read |
|------|------|
| Full audit checklist and planning questions | `references/project-analysis.md` |
| Config precedence, scope selection, and plugin directories | `references/config-layering.md` |
| Current official hook surfaces, event groups, and special plugin capabilities | `references/hook-events.md` |
| Common plugin archetypes like guardrails, post-turn checks, shell env, and custom tools | `references/plugin-patterns.md` |
| Managed folder layout and plan file shape | `references/scaffold-layout.md` |
| Additive versus overhaul behavior | `references/merge-strategy.md` |
| Runtime traps, path drift, cache issues, and JSONC caveats | `references/gotchas.md` |

## Operational Scripts

- `scripts/audit_project.sh` builds a project profile from real repo signals.
- `scripts/check_plugin_setup.ts` inspects project and global OpenCode config, plugin directories, and config-dir package files.
- `scripts/merge_opencode_config.ts` preserves unrelated config keys while merging plugin-array entries into `opencode.json` or `opencode.jsonc`.
- `scripts/merge_package_json.ts` preserves unrelated package fields while merging config-dir dependencies needed by local plugins.
- `scripts/scaffold_hooks.sh` renders live managed plugin modules, hook-surface stubs, the manifest, and the plugin README.
- `scripts/render_hooks_readme.sh` rebuilds `.opencode/plugins/README.md` from the manifest and the current plan.
- `templates/hook-plan.example.json` is the minimal lifecycle/action scaffold.
- `templates/hook-plan.broad.example.json` is the broad surface-catalog scaffold.
- `scripts/validate.py` checks structure, frontmatter, manifest integrity, and cross-references.
- `scripts/test_skill.py` runs lightweight validation plus temp-project integration checks.

## Gotchas

1. OpenCode hooks are plugins, not a separate hook-config file.
2. All plugins from all sources load in sequence, so a project-local scaffold does not replace global plugins.
3. Use the documented plugin directories: project-local `.opencode/plugins/` and global `~/.config/opencode/plugins/`.
4. `tool.execute.after` is reactive, not preventative. Use `tool.execute.before` for guardrails.
5. `event` plus named event handlers can double-handle the same workflow if you do not keep ownership clear.
6. Local plugin dependencies belong in the config directory package file, not in the repo root package by default.
7. `experimental.session.compacting` is real in the docs examples, but it is explicitly experimental.
8. OpenCode startup issues often trace back to bad plugins or stale cache, so troubleshooting sometimes matters more than rewriting logic.
