# Hook Events

Current official Claude Code hook event catalog, verified against the official docs on 2026-04-10.

Official sources:

- `https://code.claude.com/docs/en/hooks`
- `https://code.claude.com/docs/en/hooks-guide`

Use `assets/hook-events.json` as the deterministic scaffold input. Re-verify the official docs before every real scaffold or refresh.

## Support Matrix

Events that support all four hook types: `command`, `http`, `prompt`, and `agent`

- `PermissionRequest`
- `PostToolUse`
- `PostToolUseFailure`
- `PreToolUse`
- `Stop`
- `SubagentStop`
- `TaskCompleted`
- `TaskCreated`
- `UserPromptSubmit`

Events that support `command` and `http` only

- `ConfigChange`
- `CwdChanged`
- `Elicitation`
- `ElicitationResult`
- `FileChanged`
- `InstructionsLoaded`
- `Notification`
- `PermissionDenied`
- `PostCompact`
- `PreCompact`
- `SessionEnd`
- `StopFailure`
- `SubagentStart`
- `TeammateIdle`
- `WorktreeCreate`
- `WorktreeRemove`

Event that supports `command` only

- `SessionStart`

`async: true` is documented in the official reference. It only works on command hooks. Async hooks cannot block or control Claude after the triggering action has already continued.

## Event Table

| Event | Primary use | Matcher | Hook types | Async guidance |
|------|--------------|---------|------------|----------------|
| `SessionStart` | bootstrap, rehydrate, session reminders | startup mode like `startup`, `resume`, `clear`, `compact` | `command` | Keep sync for bootstrap work |
| `InstructionsLoaded` | react when Claude loads rules or memory files | load reason | `command`, `http` | Use async only for passive logging |
| `UserPromptSubmit` | validate or reshape prompts before work begins | none | all four | Keep sync when you must gate |
| `PreToolUse` | hard gates before a tool runs | tool name | all four | Usually sync |
| `PermissionRequest` | custom allow or deny decisions for permission prompts | tool name | all four | Usually sync |
| `PermissionDenied` | react to an auto-mode denial, optionally suggest retry | tool name | `command`, `http` | Usually sync |
| `PostToolUse` | post-success format, tests, logging, notifications | tool name | all four | Strong async candidate for side effects |
| `PostToolUseFailure` | failure logging, alerts, retries, follow-up hints | tool name | all four | Async for alerts, sync for retry logic |
| `Notification` | desktop alerts or external notifications | notification type | `command`, `http` | Usually async |
| `SubagentStart` | observe subagent startup or record context | agent type | `command`, `http` | Often async |
| `SubagentStop` | review or log subagent results | agent type | all four | Sync for quality gates, async for logging |
| `TaskCreated` | validate or annotate task creation | none | all four | Depends on whether you gate |
| `TaskCompleted` | validate or annotate task completion | none | all four | Depends on whether you gate |
| `Stop` | decide whether Claude may stop, or run completion side effects | none | all four | Sync for gates, async for notifications |
| `StopFailure` | record API error endings | error type | `command`, `http` | Often async; output is ignored |
| `TeammateIdle` | react when an agent-team teammate is about to idle | none | `command`, `http` | Depends on whether you intervene |
| `ConfigChange` | audit or block settings changes | settings source | `command`, `http` | Async for audit, sync for policy |
| `CwdChanged` | reload environment when Claude changes directory | none | `command`, `http` | Usually sync if it updates env |
| `FileChanged` | react to watched files like `.envrc` or `.env` | changed filename | `command`, `http` | Depends on whether you update env or only log |
| `WorktreeCreate` | replace or customize worktree setup | none | `command`, `http` | Usually sync |
| `WorktreeRemove` | clean up worktrees | none | `command`, `http` | Often async unless cleanup must finish first |
| `PreCompact` | save context before compaction | compaction trigger | `command`, `http` | Usually sync |
| `PostCompact` | react after compaction | compaction trigger | `command`, `http` | Async for passive logging |
| `SessionEnd` | cleanup or audit at session shutdown | end reason | `command`, `http` | Often async unless cleanup must complete |
| `Elicitation` | intercept an MCP request for user input | MCP server name | `command`, `http` | Keep sync |
| `ElicitationResult` | rewrite or block an elicitation response | MCP server name | `command`, `http` | Keep sync |

## Tool Events With `if` Support

The official guide says `if` only works on these tool events:

- `PreToolUse`
- `PostToolUse`
- `PostToolUseFailure`
- `PermissionRequest`
- `PermissionDenied`

The official guide also says `if` requires Claude Code v2.1.85 or later.

