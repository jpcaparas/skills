# Hook Events

Current official Claude Code hook event catalog, verified against the official docs on 2026-05-26 with local Claude Code `2.1.121`.

Official sources:

- `https://code.claude.com/docs/en/hooks`
- `https://code.claude.com/docs/en/hooks-guide`

Use `assets/hook-events.json` as the deterministic scaffold input. Re-verify the official docs before every real scaffold or refresh.

## Support Matrix

Events that support all five hook types: `command`, `http`, `mcp_tool`, `prompt`, and `agent`

- `PermissionDenied`
- `PermissionRequest`
- `PostToolBatch`
- `PostToolUse`
- `PostToolUseFailure`
- `PreToolUse`
- `Stop`
- `SubagentStop`
- `TaskCompleted`
- `TaskCreated`
- `TeammateIdle`
- `UserPromptExpansion`
- `UserPromptSubmit`

Events that support `command`, `http`, and `mcp_tool`, but not `prompt` or `agent`

- `ConfigChange`
- `CwdChanged`
- `Elicitation`
- `ElicitationResult`
- `FileChanged`
- `InstructionsLoaded`
- `Notification`
- `PostCompact`
- `PreCompact`
- `SessionEnd`
- `StopFailure`
- `SubagentStart`
- `WorktreeCreate`
- `WorktreeRemove`

Events that support `command` and `mcp_tool` only

- `SessionStart`
- `Setup`

`async: true` is documented in the official reference. It only works on command hooks. Async hooks cannot block or control Claude after the triggering action has already continued.

## Event Table

| Event | Primary use | Matcher | Hook types | Async guidance |
|------|--------------|---------|------------|----------------|
| `SessionStart` | bootstrap, rehydrate, session reminders | startup mode like `startup`, `resume`, `clear`, `compact` | command + mcp_tool | Keep sync for bootstrap work |
| `Setup` | explicit init or maintenance work | `init`, `maintenance` | command + mcp_tool | Keep sync, but do not rely on it for normal startup |
| `InstructionsLoaded` | react when Claude loads rules or memory files | load reason | command + http + mcp_tool | Use async only for passive logging |
| `UserPromptSubmit` | validate or reshape prompts before work begins | none | all five | Keep sync when you must gate |
| `UserPromptExpansion` | control slash-command or MCP prompt expansion | command name | all five | Keep sync when you must gate |
| `PreToolUse` | hard gates before a tool runs | tool name | all five | Usually sync |
| `PermissionRequest` | custom allow or deny decisions for permission prompts | tool name | all five | Usually sync |
| `PermissionDenied` | react to an auto-mode denial, optionally suggest retry | tool name | all five | Usually sync |
| `PostToolUse` | post-success format, tests, logging, notifications | tool name | all five | Strong async candidate for side effects |
| `PostToolUseFailure` | failure logging, alerts, retries, follow-up hints | tool name | all five | Async for alerts, sync for retry logic |
| `PostToolBatch` | batch-level context after parallel tool calls resolve | none | all five | Sync when context must reach Claude before the next model call |
| `Notification` | desktop alerts or external notifications | notification type | command + http + mcp_tool | Usually async |
| `SubagentStart` | observe subagent startup or inject subagent context | agent type | command + http + mcp_tool | Often async unless startup context must finish first |
| `SubagentStop` | review or log subagent results | agent type | all five | Sync for quality gates, async for logging |
| `TaskCreated` | validate or annotate task creation | none | all five | Depends on whether you gate |
| `TaskCompleted` | validate or annotate task completion | none | all five | Depends on whether you gate |
| `Stop` | decide whether Claude may stop, or run completion side effects | none | all five | Sync for gates, async for notifications |
| `StopFailure` | record API error endings | error type | command + http + mcp_tool | Often async; output is ignored |
| `TeammateIdle` | react when an agent-team teammate is about to idle | none | all five | Depends on whether you intervene |
| `ConfigChange` | audit or block settings changes | settings source | command + http + mcp_tool | Async for audit, sync for policy |
| `CwdChanged` | reload environment when Claude changes directory | none | command + http + mcp_tool | Usually sync if it updates env |
| `FileChanged` | react to watched files like `.envrc` or `.env` | changed filename | command + http + mcp_tool | Depends on whether you update env or only log |
| `WorktreeCreate` | replace or customize worktree setup | none | command + http + mcp_tool | Usually sync |
| `WorktreeRemove` | clean up worktrees | none | command + http + mcp_tool | Often async unless cleanup must finish first |
| `PreCompact` | save context before compaction | compaction trigger | command + http + mcp_tool | Usually sync |
| `PostCompact` | react after compaction | compaction trigger | command + http + mcp_tool | Async for passive logging |
| `SessionEnd` | cleanup or audit at session shutdown | end reason | command + http + mcp_tool | Often async unless cleanup must complete |
| `Elicitation` | intercept an MCP request for user input | MCP server name | command + http + mcp_tool | Keep sync |
| `ElicitationResult` | rewrite or block an elicitation response | MCP server name | command + http + mcp_tool | Keep sync |

## Tool Events With `if` Support

The official guide says `if` only works on these tool events:

- `PreToolUse`
- `PostToolUse`
- `PostToolUseFailure`
- `PermissionRequest`
- `PermissionDenied`

The official guide also says `if` requires Claude Code v2.1.85 or later.
