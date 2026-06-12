# Gotchas

## 1. Exit code `2` is the blocking path

The official docs distinguish exit code `2` from other non-zero errors. Use `2` when a hook must deny an action. Exit code `1` is just an error that Devin logs.

## 2. `.devin/hooks.v1.json` has no wrapper key

The standalone hooks file is the hooks object itself. This is correct:

```json
{
  "PreToolUse": []
}
```

This is wrong for `.devin/hooks.v1.json`:

```json
{
  "hooks": {
    "PreToolUse": []
  }
}
```

## 3. Matchers are regexes, not globs

Use regexes over `tool_name`. For MCP tools, write `^mcp__github__.*`, not `mcp__github__*`.

## 4. Non-tool events have no `tool_name`

`UserPromptSubmit`, `Stop`, `PostCompaction`, `SessionStart`, and `SessionEnd` do not have a tool name. Use `""` or omit `matcher`.

## 5. Stop hooks can loop

`Stop` hooks that block can cause repeated stop attempts. Check `stop_hook_active` before blocking again, or make the condition eventually pass.

## 6. Stdout is protocol output

Command hooks can return JSON on stdout. Put diagnostics on stderr so a log line does not corrupt the decision JSON.

## 6a. Devin strictly parses stdout as Claude-format JSON

Verified in the field on 2026-06-12 (Devin CLI v2026.5.26-8): unlike Claude Code, Devin does not accept plain-text stdout from hooks. Non-empty stdout that is not valid Claude-format JSON fails Devin's effects evaluator and the entire hook output is silently discarded. The only symptom is a line in `~/.local/share/devin/cli/logs/`:

```
WARN agent_ext::hooks::event_handler: Effects evaluator failed for hook None: Failed to parse Claude hook output: expected value at line 1 column 1
```

Rules for generated Devin hook scripts:

- Emit either empty stdout or one valid Claude-format JSON object. Never plain text.
- To inject context from `SessionStart`, use:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "context text here"
  }
}
```

- Top-level fields Devin parses include `decision`, `reason`, `continue`, `stopReason`, `suppressOutput`, `systemMessage`, and `hookSpecificOutput`.

## 6b. Devin renders no hook activity in its TUI

Devin CLI applies hook effects (context injection, block decisions) but never displays hook execution in the transcript, unlike Codex CLI which prints `Running SessionStart hook` and the hook context inline. Even a parsed `systemMessage` is not rendered as of v2026.5.26-8. Silence is not failure. Verify hooks via:

- `/hooks` to list loaded hooks and their source files
- `~/.local/share/devin/cli/logs/` for `Loaded N hooks` lines and effects-evaluator warnings
- the session transcript JSON in `~/.local/share/devin/cli/transcripts/`, where injected `SessionStart` context appears as a `system` step
- asking the live agent what session context it was given

## 7. Claude config may be inherited, but it is not this scaffold's target

Devin documents that it can load Claude hook config when `read_config_from.claude` is enabled. Inspect inherited Claude hooks when debugging duplicates, but generated project hooks from this skill belong in `.devin/hooks.v1.json`.

## 8. Prompt hooks exist, but this scaffold generates command hooks

Devin documents `command` and `prompt` hook types. This scaffold is bash-first because it needs deterministic repo-owned scripts, merge behavior, and exit-code-2 blocking. Add prompt hooks manually only when the policy truly needs an LLM evaluation.

## 9. Relative commands depend on the hook process cwd

Use `$DEVIN_PROJECT_DIR` for generated command paths. It is documented as the project root environment variable and avoids surprises when Devin starts from a nested working directory.
