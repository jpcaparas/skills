# Hook Events

GitHub Copilot hooks run in two surfaces:

- Copilot cloud agent: repository hooks from `.github/hooks/*.json` inside the cloned repo.
- Copilot CLI: policy, repository, user, settings, cross-tool Claude settings, and plugin hook sources are combined.

This scaffold generates repository hooks because that is the common path for cloud agent and CLI.

## Config File Shape

Hook files use JSON with `version: 1` and a top-level `hooks` object:

```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "bash": "bash .github/copilot/hooks/generated/events/pre-tool-use.sh",
        "cwd": ".",
        "timeoutSec": 30
      }
    ]
  }
}
```

Command hooks support `bash`, `powershell`, or `command`. Cloud agent honors `bash` and `command` in its Linux sandbox and ignores `powershell`.

## Event Catalog

| Canonical Event | Alias | Cloud Agent | Output Processed | Matcher |
|-----------------|-------|-------------|------------------|---------|
| `sessionStart` | `SessionStart` | Fires once per job | Optional `additionalContext` | none |
| `sessionEnd` | `SessionEnd` | Fires once per job | No | none |
| `userPromptSubmitted` | `UserPromptSubmit` | Fires at most once | No | none |
| `preToolUse` | `PreToolUse` | Fires | Yes, permission decision | `toolName` |
| `postToolUse` | `PostToolUse` | Fires after success | Yes, result/context modification | none |
| `postToolUseFailure` | `PostToolUseFailure` | Fires after failure | Yes, recovery context | none |
| `agentStop` | `Stop` | Fires | Yes, can force continuation | none |
| `subagentStart` | none documented | Fires | Optional `additionalContext` | `agentName` |
| `subagentStop` | `SubagentStop` | Fires | Yes, can force continuation | none |
| `errorOccurred` | `ErrorOccurred` | Fires | No | none |
| `preCompact` | `PreCompact` | Fires only for `auto` trigger | No | `trigger` |
| `permissionRequest` | none documented | CLI only | Yes, allow/deny | `toolName` |
| `notification` | none documented | CLI only | Optional `additionalContext` | `notification_type` |

Use canonical camelCase event names for generated config unless the project explicitly needs VS Code-compatible snake_case payloads.

## Matcher Rules

The official docs describe matcher patterns as full-value regexes anchored as `^(?:matcher)$`.

| Event | Matcher Field |
|-------|---------------|
| `notification` | `notification_type` |
| `permissionRequest` | `toolName` |
| `preCompact` | `trigger` |
| `preToolUse` | `toolName` |
| `subagentStart` | `agentName` |

Examples:

```json
{ "matcher": "bash" }
{ "matcher": "bash|edit|create" }
{ "matcher": "web_fetch" }
```

Do not use shell globs like `bash*`. They are regexes, not globs.

## Output Decisions

### `preToolUse`

Write JSON to stdout:

```json
{
  "permissionDecision": "deny",
  "permissionDecisionReason": "Block destructive shell command"
}
```

`permissionDecision` can be `allow`, `deny`, or `ask`. Under cloud agent, `ask` behaves like `deny` because no user can answer.

### `permissionRequest`

This is Copilot CLI only. Write JSON to stdout:

```json
{
  "behavior": "deny",
  "message": "Denied by repository policy",
  "interrupt": true
}
```

For command hooks, exit code `2` is also treated as a deny and stdout JSON is merged with `{"behavior":"deny"}`.

### `agentStop` and `subagentStop`

Write JSON to stdout:

```json
{
  "decision": "block",
  "reason": "Run the missing verification before stopping."
}
```

`block` forces another agent turn using `reason`.

### `postToolUse`

Write JSON to stdout to replace or enrich a successful tool result:

```json
{
  "additionalContext": "Remember to update generated docs after this file edit."
}
```

### `postToolUseFailure`

Write `additionalContext` recovery guidance. For command hooks, exit code `2` appends stdout to the failure shown to the agent.

## Exit Codes

| Exit | Copilot Meaning |
|------|-----------------|
| `0` | Success; stdout is parsed as hook output JSON if present |
| `2` | Warning by default; `permissionRequest` treats it as deny; `postToolUseFailure` treats it as additional context |
| other non-zero | Logged and skipped for most events |
| timeout | Killed after `timeoutSec` for most events |

Exception: `preToolUse` command hooks are fail-closed. A crash, timeout, or non-zero exit other than the documented decision path denies the tool call. Prefer explicit stdout JSON and exit `0` for `preToolUse` denials.

## Cloud Agent Constraints

- Linux sandbox.
- Working directory is usually `/workspace` when the repo is cloned.
- Filesystem is ephemeral.
- Outbound network is restricted by the cloud agent firewall.
- Environment includes `GITHUB_COPILOT_API_TOKEN`, `GITHUB_COPILOT_GIT_TOKEN`, `COPILOT_AGENT_PROMPT`, and `HOME=/root`.
- `permissionRequest` has no effect because tools are pre-approved.
- `notification` does not fire because no user is present.

## See Also

- `references/scaffold-layout.md`
- `references/gotchas.md`
