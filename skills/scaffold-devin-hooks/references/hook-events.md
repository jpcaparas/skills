# Hook Events

Current documented Devin CLI hook contract, verified against the official docs on 2026-06-10.

Official sources:

- `https://docs.devin.ai/cli/extensibility/hooks/overview`
- `https://docs.devin.ai/cli/extensibility/hooks/lifecycle-hooks`

Use `assets/hook-events.json` as the deterministic scaffold input. Re-verify the official docs before every real scaffold or refresh.

## Hook File Format

Prefer project-level `.devin/hooks.v1.json`. In that file, the hooks object is the entire file:

```json
{
  "PreToolUse": [
    {
      "matcher": "^exec$",
      "hooks": [
        {
          "type": "command",
          "command": "./scripts/check-command.sh",
          "timeout": 10
        }
      ]
    }
  ]
}
```

Do not wrap this in a top-level `"hooks"` key when writing `.devin/hooks.v1.json`. The `"hooks"` wrapper is for Devin config files, not the standalone hooks file.

## Command Hook I/O

Command hooks receive a single JSON object on stdin. They may print a JSON decision on stdout:

```json
{
  "decision": "block",
  "reason": "Destructive command blocked by policy"
}
```

Documented decisions are `approve`, `block`, and `deny`. Plain logs belong on stderr so stdout stays valid JSON when the hook needs to control the outcome.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success; hook continues normally |
| `2` | Block; action is denied |
| Other non-zero | Error is logged but does not block |

Use exit code `2` for intentional policy gates. Do not use `1` when the hook must stop Devin.

## Event Table

| Event | When it fires | Stdin fields | Matcher |
|------|---------------|--------------|---------|
| `PreToolUse` | Before a tool executes | `tool_name`, `tool_input` | Regex over `tool_name` |
| `PostToolUse` | After a tool finishes | `tool_name`, `tool_input`, `tool_response` | Regex over `tool_name` |
| `PermissionRequest` | When a permission decision is needed | `tool_name`, `tool_input` | Regex over `tool_name` |
| `UserPromptSubmit` | When the user submits a message | `prompt` | No `tool_name`; use `""` or omit |
| `Stop` | When the agent wants to stop | `stop_hook_active` | No `tool_name`; use `""` or omit |
| `PostCompaction` | After context compaction succeeds | `summary` | No `tool_name`; use `""` or omit |
| `SessionStart` | When a new session begins | `source` | No `tool_name`; use `""` or omit |
| `SessionEnd` | When a session ends | `reason` | No `tool_name`; use `""` or omit |

The overview page lists the main lifecycle events and the lifecycle page documents `PostCompaction` in detail. Include `PostCompaction` unless a fresh live-doc check shows the docs changed.

## Matcher Rules

The `matcher` field is a regex matched against `tool_name`. It is meaningful for tool-related events: `PreToolUse`, `PostToolUse`, and `PermissionRequest`.

For non-tool events, there is no `tool_name`; use `""` or omit the matcher.

| Matcher | Matches |
|---------|---------|
| `""` or omitted | All tool names for tool events |
| `exec` | Tool names containing `exec` |
| `^exec$` | Only `exec` |
| `^(exec|edit)$` | Only `exec` or `edit` |
| `^mcp__.*` | All MCP tools |
| `^mcp__github__.*` | All tools from the `github` MCP server |
| `^mcp__github__create_issue$` | One exact MCP tool |

Hook matchers are not permission globs. Use `^mcp__github__.*`, not `mcp__github__*`.

## Common Tool Names

The documented common public core tool names are:

- `read`
- `edit`
- `grep`
- `glob`
- `exec`

MCP server tools appear as `mcp__<server>__<tool>`. Confirm the complete tool set for a live session by adding a temporary `PostToolUse` hook with `matcher: ""` that logs stdin.

## Environment

Devin sets `DEVIN_PROJECT_DIR` to the project root directory for hooks. Generated command paths should use it:

```json
{
  "type": "command",
  "command": "bash \"$DEVIN_PROJECT_DIR/.devin/hooks/generated/events/pre-tool-use.sh\""
}
```

## See Also

- `references/scaffold-layout.md`
- `references/gotchas.md`
