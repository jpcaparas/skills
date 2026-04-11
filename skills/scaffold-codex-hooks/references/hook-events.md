# Hook Events

Current official Codex hook catalog, verified on 2026-04-11 against the official docs, generated schemas, and open-source runtime code.

Primary sources:

- `https://developers.openai.com/codex/hooks`
- `https://github.com/openai/codex/tree/main/codex-rs/hooks/schema/generated`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/engine/discovery.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/engine/config.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/events/common.rs`

Use `assets/hook-events.json` as the deterministic scaffold input. Re-verify the official sources before every real scaffold or refresh.

## Current Runtime Model

- Current official events: `SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`
- Current supported handler type in practice: `command`
- `prompt` and `agent` parse in config but the runtime skips them
- `async` parses in config but the runtime skips it
- Default timeout: `600` seconds
- Timeout alias: `timeoutSec`

## Support Matrix

| Event | Matcher support | Matcher target today | Plain text stdout | JSON stdout | Blocking / control note |
|------|------------------|----------------------|-------------------|-------------|-------------------------|
| `SessionStart` | Yes | `source` (`startup` or `resume`) | Added as additional developer context | `hookSpecificOutput.additionalContext` | No dedicated block shape |
| `PreToolUse` | Yes | `tool_name`, currently always `Bash` | Ignored | `permissionDecision: "deny"` or legacy `decision: "block"` | Can block the Bash command before it runs |
| `PostToolUse` | Yes | `tool_name`, currently always `Bash` | Ignored | `additionalContext`, `decision: "block"`, `continue: false` | Cannot undo side effects from the command that already ran |
| `UserPromptSubmit` | No | Matcher ignored | Added as additional developer context | `additionalContext` or `decision: "block"` | Can block the prompt before it is sent |
| `Stop` | No | Matcher ignored | Invalid when exiting `0` | `decision: "block"` or shared output fields | `decision: "block"` means "continue Codex with this new prompt" |

## Important Limits

- `PreToolUse` and `PostToolUse` only support Bash tool interception today.
- Those two events do not currently intercept every shell call; simple Bash calls are the reliable target.
- They do not currently intercept `Write`, `WebSearch`, `MCP`, or other non-shell tool calls.
- `matcher: "*"` and `matcher: ""` both mean match all.
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
- `permissionDecision: "allow"` and `"ask"` are parsed but not supported yet, so they fail open.

### PostToolUse

- `decision: "block"` does not roll back the command.
- `continue: false` stops normal processing of the original tool result after the command already ran.
- `updatedMCPToolOutput` is parsed but not supported yet.

### UserPromptSubmit

- Plain text on stdout becomes extra developer context.
- `decision: "block"` blocks the prompt before it is sent.

### Stop

- Plain text stdout is invalid for this event when the hook exits `0`.
- `decision: "block"` tells Codex to continue and creates a new continuation prompt using your `reason`.
- If a matching `Stop` hook returns `continue: false`, that takes precedence over continuation decisions from other matching `Stop` hooks.
