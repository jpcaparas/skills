# Gotchas

## 1. OpenCode hooks are plugins, not a standalone hook config

If you scaffold as though OpenCode had a `hooks.json` equivalent, you will create the wrong file structure. The real runtime unit is a plugin module.

## 2. Use the documented plugin directories

Use project-local `.opencode/plugins/` and global `~/.config/opencode/plugins/` when scaffolding or troubleshooting plugin loading.

## 3. Local and npm plugins can both load

OpenCode loads plugins from config files and local directories. A local plugin and an npm plugin with a similar name can both run.

## 4. `tool.execute.after` cannot prevent side effects

Use `tool.execute.before` when the plugin must stop or rewrite an action. Use `tool.execute.after` only for observation, bookkeeping, or feedback after the fact.

## 5. `event` plus named handlers can overlap

If a plugin uses `event` and also subscribes to a specific named surface, you can easily double-handle the same workflow unless one of them owns the coordination.

## 6. Config-dir dependencies live under `.opencode/` or `~/.config/opencode/`

Do not default to the repo root `package.json` when the plugin runtime dependency only exists for OpenCode local plugins. The docs explicitly point the dependency install to the config directory.

## 7. `experimental.session.compacting` is not a baseline safety primitive

It is shown in the official docs, but it is explicitly experimental. Use it for enrichment, not for critical policy.

## 8. Bad plugins can break startup

The troubleshooting docs explicitly recommend disabling plugins and clearing `~/.cache/opencode` when OpenCode hangs, crashes, or behaves strangely.

## 9. JSONC comments will not survive deterministic merges

This skill can read JSONC config, but the managed merge scripts write normalized JSON output. Warn the user before you rewrite a hand-commented config file.

## 10. Post-turn checks need both state and cooldown

Without edit tracking and a cooldown, a `session.idle`-driven validator can thrash the agent with repeated lint or test prompts.
