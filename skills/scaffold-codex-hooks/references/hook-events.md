# Hook Events

Current Codex hook catalog, verified on 2026-05-08 against the official docs, generated schemas, local Codex CLI 0.129.0, and open-source runtime code at `a3de5bde6e6cc33140f1b0af9afc3beea68ca1a2`.

Primary sources:

- `https://developers.openai.com/codex/hooks`
- `https://github.com/openai/codex/tree/main/codex-rs/hooks/schema/generated`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/lib.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/config/src/hook_config.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/events/common.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/events/compact.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/events/permission_request.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/core/src/tools/hook_names.rs`

Use `assets/hook-events.json` as the deterministic scaffold input. Re-verify the official sources before every real scaffold or refresh.

## Current Runtime Model

- Current source-backed events: `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionStart`, `UserPromptSubmit`, `Stop`
- Current supported handler type in practice: `command`
- `prompt` and `agent` parse in config but the runtime skips them
- `async` parses in config but the runtime skips it
- Default timeout: `600` seconds
- Timeout alias: `timeoutSec`
- Canonical feature key: `hooks`; legacy alias: `codex_hooks`

## Support Matrix

| Event | Matcher support | Matcher target today | Plain text stdout | JSON stdout | Blocking / control note |
|------|------------------|----------------------|-------------------|-------------|-------------------------|
| `SessionStart` | Yes | `source` (`startup`, `resume`, `clear`) | Added as additional developer context | Common fields plus `hookSpecificOutput.additionalContext` | No dedicated block shape |
| `UserPromptSubmit` | No | Matcher ignored | Added as additional developer context | `additionalContext` or `decision: "block"` | Can block the prompt before it is sent |
| `PreToolUse` | Yes | `tool_name` plus aliases | Ignored | `additionalContext`, `permissionDecision: "deny"`, or legacy `decision: "block"` | Can block supported tool calls before they run |
| `PermissionRequest` | Yes | `tool_name` plus aliases | Ignored | `hookSpecificOutput.decision.behavior` as `allow` or `deny` | Any deny wins; otherwise allow can bypass the normal prompt |
| `PostToolUse` | Yes | `tool_name` plus aliases | Ignored | `additionalContext`, `decision: "block"`, `continue: false` | Cannot undo side effects from the tool that already ran |
| `PreCompact` | Yes | `trigger` (`manual` or `auto`) | Ignored | Common fields; `continue: false` stops compaction | `decision: "block"` is invalid |
| `PostCompact` | Yes | `trigger` (`manual` or `auto`) | Ignored | Common fields; `continue: false` stops follow-on processing | `decision: "block"` is invalid |
| `Stop` | No | Matcher ignored | Invalid when exiting `0` | `decision: "block"` or shared output fields | `decision: "block"` means "continue Codex with this new prompt" |

## Important Limits

- `PreToolUse`, `PermissionRequest`, and `PostToolUse` can match Bash, `apply_patch`, and MCP tool paths when those paths expose hook payloads.
- File-edit hooks expose canonical `tool_name: "apply_patch"`; matcher aliases `Edit` and `Write` can select the same hook.
- MCP hooks use namespaced tool names such as `mcp__server__tool`.
- Hooks still do not intercept `WebSearch`, every shell pathway, or every possible tool implementation.
- `matcher: "*"` and `matcher: ""` both mean match all for matcher-aware events.
- `matcher` is ignored entirely for `UserPromptSubmit` and `Stop`.

## Output Semantics That Matter

### PreToolUse

- Preferred deny shape:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Destructive command blocked by hook."
  }
}
```

- Legacy block shape still accepted:

```json
{
  "decision": "block",
  "reason": "Destructive command blocked by hook."
}
```

- Exit code `2` plus a reason on `stderr` also blocks.
- `hookSpecificOutput.additionalContext` is accepted.
- `permissionDecision: "allow"`, `permissionDecision: "ask"`, `updatedInput`, `continue: false`, `stopReason`, and `suppressOutput` are not supported.

### PermissionRequest

- Allow shape:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "allow"
    }
  }
}
```

- Deny shape:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "decision": {
      "behavior": "deny",
      "message": "Blocked by repository policy."
    }
  }
}
```

- Exit code `2` plus a reason on `stderr` also denies.
- Any matching deny wins over matching allows.
- `updatedInput`, `updatedPermissions`, `interrupt`, `continue: false`, `stopReason`, and `suppressOutput` are not supported.

### PostToolUse

- `decision: "block"` does not roll back the tool call.
- `continue: false` stops normal processing of the original tool result after the tool already ran.
- Exit code `2` plus stderr provides feedback to Codex.
- `hookSpecificOutput.additionalContext` is accepted.
- `updatedMCPToolOutput` and `suppressOutput` are not supported.

### PreCompact And PostCompact

- `matcher` applies to the compaction `trigger`: `manual` or `auto`.
- Plain text stdout is ignored.
- `continue: false` with optional `stopReason` stops the compaction flow at that stage.
- `decision: "block"` is invalid for these events.

### UserPromptSubmit

- Plain text on stdout becomes extra developer context.
- JSON can return `hookSpecificOutput.additionalContext`.
- `decision: "block"` blocks the prompt before it is sent.

### Stop

- Plain text stdout is invalid for this event when the hook exits `0`.
- `decision: "block"` tells Codex to continue and creates a new continuation prompt using your `reason`.
- If a matching `Stop` hook returns `continue: false`, that takes precedence over continuation decisions from other matching `Stop` hooks.
