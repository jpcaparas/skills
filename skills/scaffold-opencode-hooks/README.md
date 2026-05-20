# scaffold-opencode-hooks

Repository-agnostic skill for auditing a project and scaffolding OpenCode hooks as managed OpenCode plugins.

## What It Adds

- live-doc verification against the current official OpenCode plugin, config, SDK, custom-tools, and troubleshooting docs
- a deep project audit before any plugin plan is chosen
- deterministic inspection of project-vs-global OpenCode plugin state
- a minimal TypeScript lifecycle/action plugin by default for repo-owned validation, session context, and post-action automation
- visible OpenCode TUI feedback through best-effort toasts, with diagnostic logs kept separate
- one controlled automatic repair/follow-up prompt for automatable failures
- optional broad hook-surface stub coverage only when the user asks for a broad scaffold
- repeatable merges for `opencode.json` plugin arrays and config-dir dependencies when the plan actually needs them
- additive and overhaul refresh modes for projects that already use OpenCode plugins
- a generated `.opencode/plugins/README.md` so the target project has a concise map of active behavior

## Key Files

- `SKILL.md` for the authoritative workflow
- `references/project-analysis.md` for the audit checklist
- `references/config-layering.md` for scope, precedence, and directory guidance
- `references/hook-events.md` for the current surface catalog and lifecycle semantics
- `references/plugin-patterns.md` for lifecycle/action, repair, toast, guardrail, post-turn, shell env, and custom-tool patterns
- `references/scaffold-layout.md` for the generated target structure
- `references/merge-strategy.md` for repeat-run behavior
- `references/gotchas.md` for runtime limits, path drift, and cache traps
- `scripts/audit_project.sh` to profile a real project
- `scripts/check_plugin_setup.ts` to inspect OpenCode config and plugin directories
- `scripts/scaffold_hooks.sh` to build or refresh the managed plugin scaffold
- `scripts/merge_opencode_config.ts` to merge npm plugin entries into config
- `scripts/merge_package_json.ts` to merge config-dir dependencies for local plugins
- `assets/hook-events.json` for the current static hook-surface manifest used by the deterministic scaffold
