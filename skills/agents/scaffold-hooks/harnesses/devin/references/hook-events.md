# Hook Events

Bundled Devin CLI hook baseline, verified against the official docs on 2026-06-10. The JSON context/decision guidance below was also checked against the official overview on 2026-09-25; this does not re-certify every bundled event field.

Official sources:

- `https://docs.devin.ai/cli/extensibility/hooks/overview`
- `https://docs.devin.ai/cli/extensibility/hooks/lifecycle-hooks`

Use `assets/hook-events.json` as the deterministic scaffold input. Consult relevant official docs when installed evidence is insufficient, stale, or event semantics will change. Propose canonical updates through the root `SKILL.md` maintenance route; do not silently edit installed inputs.

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

The official overview's output table documents `approve` and `block`. Older package evidence also lists `deny`; verify it against the target release before using it rather than treating it as interchangeable. Plain logs belong on stderr so stdout stays valid JSON when the hook needs to control the outcome.

Historical field evidence (2026-06-12, v2026.5.26-8): Devin rejected plain-text stdout in its effects evaluator and silently dropped it, logging `Failed to parse Claude hook output` in `~/.local/share/devin/cli/logs/`. That version is a verification baseline, not an installation requirement. Generated scripts must emit empty stdout or one event-appropriate Devin JSON object; a parser's Claude-related error text does not prove general Claude compatibility.

To inject context from `SessionStart`, emit this specifically documented Devin `hookSpecificOutput` shape:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "context text here"
  }
}
```

In the field-tested baseline, Devin injected `additionalContext` as a system message before the user's first prompt without rendering hook activity in the TUI. Verify injection via `/hooks`, CLI logs, or transcript JSON under `~/.local/share/devin/cli/transcripts/`; do not assume later UI behavior is identical. See `references/gotchas.md` items 6a and 6b.

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
  "command": "bash \"$DEVIN_PROJECT_DIR/hooks/pre-tool-use/devin.sh\""
}
```

## See Also

- `references/scaffold-layout.md`
- `references/gotchas.md`
