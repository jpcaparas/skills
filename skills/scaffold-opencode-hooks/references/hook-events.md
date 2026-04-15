# Hook Surfaces

Current OpenCode hook surface catalog, verified on 2026-04-15 against the official plugin, config, SDK, custom-tools, and troubleshooting docs.

Primary sources:

- `https://opencode.ai/docs/plugins/`
- `https://opencode.ai/docs/config/`
- `https://opencode.ai/docs/sdk`
- `https://opencode.ai/docs/custom-tools`
- `https://opencode.ai/docs/troubleshooting`

Secondary source:

- `https://blog.devgenius.io/opencode-auto-lint-your-ai-agents-code-with-a-post-turn-biome-hook-7158d75c63db?postPublishedType=repub`

Use `assets/hook-events.json` as the deterministic scaffold input. Re-verify the official docs before every real scaffold or refresh.

## Current Runtime Model

- OpenCode hooks are plugin modules, not a separate hook config file.
- Plugins can load from local files or npm packages.
- Local plugin files load from `.opencode/plugins/` or `~/.config/opencode/plugins/`.
- npm plugin packages load through the `plugin` array in config.
- All plugins from all sources run in sequence using the documented load order.

## Special Plugin Surfaces

These are not just named event strings, but they materially change how you scaffold plugins:

| Surface | What it does | Notes |
|--------|---------------|-------|
| `event` | Catch-all event observer | Use this when a plugin needs to react to many event types or watch for `session.idle` |
| `tool` | Register custom tools | Requires `@opencode-ai/plugin` for the `tool()` helper in the official examples |
| `experimental.session.compacting` | Modify compaction context or prompt | Experimental; opt in carefully |

## High-Value Hook Surfaces

| Surface | Best use | Why it matters |
|--------|----------|----------------|
| `tool.execute.before` | guardrails and rewrites | Runs before the tool executes |
| `tool.execute.after` | edit tracking and post-action observation | Good for marking state, not prevention |
| `event` + `session.idle` | post-turn validation | Lets a plugin wait for the agent to go idle before running checks |
| `shell.env` | environment injection | Safely adds env vars to shell execution |
| `tool` | custom tools | Extends OpenCode beyond built-in tools |
| `experimental.session.compacting` | custom continuation context | Helps preserve domain state across compaction |

## Official Event Groups

### Command Events

- `command.executed`

### File Events

- `file.edited`
- `file.watcher.updated`

### Installation Events

- `installation.updated`

### LSP Events

- `lsp.client.diagnostics`
- `lsp.updated`

### Message Events

- `message.part.removed`
- `message.part.updated`
- `message.removed`
- `message.updated`

### Permission Events

- `permission.asked`
- `permission.replied`

### Server Events

- `server.connected`

### Session Events

- `session.created`
- `session.compacted`
- `session.deleted`
- `session.diff`
- `session.error`
- `session.idle`
- `session.status`
- `session.updated`

### Todo Events

- `todo.updated`

### Shell Events

- `shell.env`

### Tool Events

- `tool.execute.after`
- `tool.execute.before`

### TUI Events

- `tui.prompt.append`
- `tui.command.execute`
- `tui.toast.show`

## Practical Semantics

- Use `tool.execute.before` when the plugin needs to deny or rewrite a tool call.
- Use `tool.execute.after` when the plugin only needs to observe what just happened.
- Use `event` when the logic needs cross-event state, especially idle detection after edits.
- Use `client.session.prompt()` when the plugin needs to feed results back into a session.
- Use `client.app.log()` for structured logs instead of `console.log()`.
- Use config-dir dependencies only when the plugin imports external packages.

