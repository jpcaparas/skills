# OpenCode Hook Events

The OpenCode harness writes one generated native plugin, `.opencode/plugins/scaffold-hooks.ts` (global scope: `~/.config/opencode/plugins/scaffold-hooks.ts`). OpenCode loads every `.ts` or `.js` file in a `plugins/` directory without a config entry, so the scaffold touches no `opencode.json`.

Read on 2026-11-10 and run live on 2026-11-11 against OpenCode 1.19.5 (`opencode-ai`, `@opencode-ai/plugin`, `@opencode-ai/sdk`) and the docs at `https://opencode.ai/docs/plugins/`, `https://opencode.ai/docs/build/plugins` and `https://opencode.ai/docs/build/plugins/server`. `assets/hook-events.json` is the machine-readable form.

## Plugin API

The plugin exports `{ id, server(input) }`, the V1 shape: `server` returns hooks by string key plus an `event` handler. Checked live on 2026-11-11: OpenCode 1.19.5 (latest), its `beta` tag (0.0.0-beta-202608110357) and `dev` tag (0.0.0-dev-202611092046) each called `server()` and none called the documented V2 `setup(ctx)`, so the generated plugin has no V2 half. Add one only after a release is seen running it.

## Events a plan can use

| Plan event | OpenCode hook | Behaviour |
| --- | --- | --- |
| `session.created` | `event` with `type: "session.created"` | Runs the scripts for a main session. Output is not injected into the model context; failures are logged. |
| `session.idle` | `event` with `type: "session.idle"` | The end-of-turn check. Gated by `run_on_code_changes` (default on) and `code_change_extensions`. A failure sends its output back to the session as a prompt once. |
| `tool.execute.before` | `hooks["tool.execute.before"]` | `matcher` is a regex over the tool name. A failure throws, which blocks the tool; the model sees the failure text as the tool error. |
| `tool.execute.after` | `hooks["tool.execute.after"]` | Same matcher. A failure is logged; the tool already ran. |

Not supported: permission hooks, prompt/message hooks, compaction hooks, other session and file events. A plan naming any other event is rejected.

## Guarantees

- No stop hook can block in OpenCode, so `session.idle` resumes the session with the failure text through `session.promptAsync` and skips that session's next idle. That is the `stop_hook_active` guard.
- Sessions with a `parentID` (subagents) are ignored, replacing Froggy's `isMainSession`.
- Malformed `scripts` or `commands` fail the scaffold; if the plugin is edited by hand into a malformed state it fails closed at run time instead of running anything.
- Scripts get `AGENT_HOOK_HARNESS`, `AGENT_HOOK_EVENT`, `AGENT_HOOK_PROJECT_ROOT`, `AGENT_HOOK_SESSION_ID` and one JSON object on stdin (`hook_event_name`, `session_id`, `cwd`, plus `tool_name` and `tool_input` for tool events and `stop_hook_active` for `session.idle`).

## Plan shape

```json
{ "scope": "project", "enabled_events": [ { "name": "session.idle", "timeout": 300, "scripts": [ { "path": "scripts/agent-stop-checks.sh", "args": ["opencode"] } ] } ] }
```

`plugin_target` overrides the output path. `scope: "global"` needs `--allow-global-targets` and stays under `~/.config/opencode/`.

## Migrating from opencode-froggy

Earlier scaffolds wrote `.opencode/hook/hooks.md` and an `opencode-froggy` entry in `opencode.json`. `opencode-froggy` 1.7.0 (2026-11-01) and later no longer load `hooks.md`, and OpenCode deprecates the `plugin` config key for `plugins`. A refresh deletes the managed block between the `scaffold-hooks managed opencode-froggy` markers (and the file if nothing else is left), the exact `opencode-froggy` entry in `opencode.json` and `.opencode/hook/.managed`, and only when that state proves the scaffold wrote it. A pinned `opencode-froggy@x` entry is treated as the user's and kept.
