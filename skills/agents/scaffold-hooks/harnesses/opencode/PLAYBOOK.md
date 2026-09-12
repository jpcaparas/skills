# OpenCode Harness Playbook

Internal component of the `scaffold-hooks` skill. This playbook owns the OpenCode integration, which now installs `opencode-froggy` and renders Froggy's hook configuration instead of generating local TypeScript lifecycle plugins.

## Decision Tree

What is the user asking for?

- New OpenCode hooks in a repo:
  Verify the current OpenCode plugin docs and `opencode-froggy` package, audit the repo, then scaffold `opencode.json` plus `.opencode/hook/hooks.md`.
- Existing old scaffold under `.opencode/plugins/.managed/`:
  Treat it as a migration. Raze scaffold-owned `.opencode/plugins/*.ts`, `.opencode/package.json` dependency artifacts, and `hooks/opencode-session-*` adapters, then install Froggy and render `hooks.md`.
- Existing custom `.opencode/hook/hooks.md`:
  Preserve it. Append the managed Froggy block only when the file has an appendable `hooks:` frontmatter list; otherwise stop with a clear manual-merge error.
- Existing custom `.opencode/plugins/*.ts`:
  Preserve unmanaged plugin files. Froggy does not replace all OpenCode plugins; it replaces only the old scaffold-owned hook adapter.
- Personal cross-repo OpenCode hooks:
  Use global scope so config lands under `~/.config/opencode/opencode.json` and `~/.config/opencode/hook/hooks.md`.
- Explanation only:
  Read `references/hook-events.md`, `references/config-layering.md`, `references/scaffold-layout.md`, and `references/merge-strategy.md`, then answer without scaffolding.

## Quick Reference

| Task | Action |
|------|--------|
| Verify official OpenCode plugin/config docs | Read `https://opencode.ai/docs/plugins/` and `https://opencode.ai/docs/config/` |
| Verify Froggy hook semantics | Inspect `https://github.com/smartfrog/opencode-froggy`, especially `src/index.ts`, `src/loaders.ts`, `src/bash-executor.ts`, and `README.md` |
| Audit a target repo | Run `scripts/audit_project.sh /path/to/project` |
| Inspect OpenCode setup | Run `bun scripts/check_plugin_setup.ts --project /path/to/project --json` |
| Merge `opencode-froggy` into OpenCode config | Run `bun scripts/merge_opencode_config.ts --config-file /path/to/opencode.json --plugins opencode-froggy` |
| Render Froggy `hooks.md` | Run `bun scripts/render_froggy_hooks.ts --hooks-file /path/to/.opencode/hook/hooks.md --hooks-json '[...]'` |
| Scaffold OpenCode | Run `bash scripts/scaffold_hooks.sh --project /path/to/project --plan /path/to/plan.json --mode additive|overhaul` |
| Regenerate hook README | Run `bash scripts/render_hooks_readme.sh --project /path/to/project --plan /path/to/plan.json` |

## Non-Negotiable Workflow

1. Verify live OpenCode plugin/config docs and current `opencode-froggy` source before changing event semantics.
2. Compare that ground truth with `assets/hook-events.json`.
3. Audit the target repo before choosing project or global scope.
4. Inspect `opencode.json`, `opencode.jsonc`, `.opencode/hook/hooks.md`, `.opencode/plugins/`, `.opencode/package.json`, AGENTS files, and repo-owned scripts.
5. Start from `templates/hook-plan.example.json`; use `templates/hook-plan.broad.example.json` only when the user wants examples for tool hooks too.
6. Run a dry run first through the universal skill when possible.
7. Scaffold. The resulting active OpenCode files should be `opencode.json` and `.opencode/hook/hooks.md`.
8. Confirm old managed plugin scaffolding was removed when `.opencode/plugins/.managed/manifest.json` proved scaffold ownership.
9. Confirm no `.opencode/package.json`, lockfile, or `node_modules` was created by the default Froggy scaffold.
10. Run this component's validator and test suite.

## Froggy Contract

`opencode-froggy` is loaded as an npm plugin by OpenCode:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["opencode-froggy"]
}
```

Froggy loads hooks from:

- project: `.opencode/hook/hooks.md`
- global: `~/.config/opencode/hook/hooks.md`
- Windows fallback for global hooks: `%APPDATA%/opencode/hook/hooks.md`

The hook file is Markdown with YAML frontmatter:

```markdown
---
hooks:
  - event: session.idle
    conditions: [isMainSession]
    actions:
      - bash: "npm run lint"
---
```

Supported Froggy events:

- `session.created`
- `session.deleted`
- `session.idle`
- `tool.before.*`
- `tool.before.<name>`
- `tool.after.*`
- `tool.after.<name>`

Supported conditions:

- `isMainSession`
- `hasCodeChange`

Supported actions:

- `bash`
- `command`
- `tool`

## Migration Rules

When an old scaffold-owned OpenCode setup exists:

- read `.opencode/plugins/.managed/manifest.json`
- delete only managed plugin files listed in `managed_files`
- delete `.opencode/plugins/README.md` when it is the generated scaffold README
- remove `.opencode/plugins/.managed/`
- remove generated `hooks/opencode-session-created` and `hooks/opencode-session-idle` adapters only when they still match the old generated shape
- remove `.opencode/package.json`, lockfiles, and `node_modules` only when the package file contains only the old `@opencode-ai/plugin` dependency
- leave unrelated custom OpenCode plugins alone

This cleanup is intentionally part of additive runs too. If a repo was scaffolded the previous way, a normal rerun should migrate it to Froggy without requiring a separate cleanup command.

## Plan Shape

Use `templates/hook-plan.example.json` as the source of truth. Important fields:

- `scope`: `project` or `global`
- `mode`: `additive` or `overhaul`
- `plugin_name`: must be `opencode-froggy`
- `config_target`: normally `opencode.json`
- `hook_config_target`: normally `.opencode/hook/hooks.md`
- `managed_state_dir`: normally `.opencode/hook/.managed`
- `hooks`: Froggy hook entries with `event`, optional `conditions`, `actions`, and `notes`

Keep project-specific validation in repo-owned scripts. The default plan calls scripts only if they exist:

- `./scripts/agent-session-context.sh` from `session.created`
- `./scripts/validate-project.sh` from `session.idle`

Project plans can swap `./scripts/validate-project.sh` for `./scripts/agent-stop-checks.sh` or another repo-owned command.

## Repeat-Run Rules

- Replace the managed block between `BEGIN scaffold-hooks managed opencode-froggy` and `END scaffold-hooks managed opencode-froggy`.
- Append the managed block to an existing custom `hooks:` list only when it is structurally safe.
- Refuse to overwrite unrecognized custom `hooks.md` structures.
- Preserve unrelated entries in `opencode.json` while adding `opencode-froggy`.
- Preserve unmanaged local plugin files in `.opencode/plugins/`.
- Remove old scaffold-owned plugin files when the old manifest proves ownership.

## Progressive Maintainer Drift Check

When updating this skill itself:

1. Live-fetch the official OpenCode plugin and config docs on the day of the edit.
2. Check `npm view opencode-froggy --json`, `npm view @opencode-ai/plugin version`, and local `opencode --version` when available.
3. Read the current Froggy source for hook loading, event handling, bash execution, and config paths.
4. Update `assets/hook-events.json` first if the contract changed.
5. Then update scaffold scripts, templates, references, validators, tests, evals, and wrappers.
6. Do not update this skill from memory.

## Reading Guide

| Need | Read |
|------|------|
| Full audit checklist | `references/project-analysis.md` |
| Config precedence and scope | `references/config-layering.md` |
| Froggy events/actions/conditions | `references/hook-events.md` |
| Common Froggy hook patterns | `references/plugin-patterns.md` |
| Managed layout and plan fields | `references/scaffold-layout.md` |
| Reusable repo-owned script placement | `references/reusable-scripts.md` |
| Additive vs overhaul behavior | `references/merge-strategy.md` |
| Runtime traps and migration gotchas | `references/gotchas.md` |

## Operational Scripts

- `scripts/audit_project.sh` builds a project profile from real repo signals.
- `scripts/check_plugin_setup.ts` inspects OpenCode config, Froggy hook files, and legacy plugin scaffolds.
- `scripts/merge_opencode_config.ts` preserves unrelated config keys while adding `opencode-froggy`.
- `scripts/render_froggy_hooks.ts` renders or refreshes the managed block in `hooks.md`.
- `scripts/scaffold_hooks.sh` orchestrates Froggy install, managed hook rendering, legacy cleanup, manifest writing, and README generation.
- `scripts/render_hooks_readme.sh` rebuilds `.opencode/hook/README.md`.
- `scripts/validate.py` checks structure, manifest integrity, and cross-references.
- `scripts/test_skill.py` runs temp-project integration checks.

## Gotchas

1. Froggy hooks still require an OpenCode plugin. `opencode.json` must include `opencode-froggy`.
2. Froggy hook config lives under `.opencode/hook/`, singular, while OpenCode local plugins live under `.opencode/plugins/`, plural.
3. Froggy global hooks run before project hooks; a project scaffold does not disable personal global hooks.
4. `hasCodeChange` follows Froggy's code-extension list and does not include Markdown. Do not use it for skills repositories unless Markdown-only changes may skip validation.
5. Bash actions always send a hook result back to the session. Redirect noisy stdout when a script is only recording baseline state.
6. `tool.before.*` and `tool.before.<name>` can block by exiting `2`; other nonzero bash exits are reported but non-blocking in Froggy.
7. Do not recreate the old toast/repair TypeScript adapter unless the user explicitly asks for custom OpenCode plugin code.
