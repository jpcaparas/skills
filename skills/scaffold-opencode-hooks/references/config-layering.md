# Config Layering

Verified against the official OpenCode config and plugin docs on 2026-04-15.

## Config Precedence

OpenCode merges config sources instead of replacing them. The documented order is:

1. remote config from `.well-known/opencode`
2. global config `~/.config/opencode/opencode.json`
3. custom config from `OPENCODE_CONFIG`
4. project config `opencode.json`
5. `.opencode` directories for agents, commands, plugins, and related files
6. inline config from `OPENCODE_CONFIG_CONTENT`
7. managed config files
8. macOS managed preferences

That means a project-local scaffold never fully replaces global config, and a project-local plugin directory never removes global plugin behavior.

## Plugin Locations

Official plugin directories:

- project local: `.opencode/plugins/`
- global: `~/.config/opencode/plugins/`

Official config file locations:

- project local: `opencode.json` or `opencode.jsonc`
- global: `~/.config/opencode/opencode.json` or `~/.config/opencode/opencode.jsonc`

## Local Plugin Dependencies

If local plugins need external npm packages, add a `package.json` to the matching config directory:

- project local -> `.opencode/package.json`
- global -> `~/.config/opencode/package.json`

OpenCode runs `bun install` at startup for those config-dir dependencies.

The managed scaffold may also create that config-dir `package.json` to normalize `"type": "module"` for local JavaScript plugin modules, even when there are no extra dependencies yet.

## Scope Guidance

Use project-local scope when:

- the behavior should travel with the repo
- teammates should see the same hooks
- the plugin logic depends on repo-local paths or workflows

Use global scope when:

- the behavior is personal or machine-local
- the repo should not contain OpenCode plugin files
- the same hook should apply across many repos

## Config Format Guidance

The official docs support both JSON and JSONC. This skill’s deterministic merge scripts can read JSON or JSONC, but they write normalized JSON output. If a user’s config file currently contains comments, warn them that comments will not be preserved by the managed merge.

## Troubleshooting Hooks vs Config

When OpenCode behaves strangely, inspect this order before rewriting plugin logic:

1. global config file
2. project config file
3. global plugin directory
4. project plugin directory
5. config-dir `package.json`
6. cache at `~/.cache/opencode`
7. logs at `~/.local/share/opencode/log/`

The troubleshooting docs explicitly recommend disabling plugins and clearing cache before assuming the runtime itself is broken.
