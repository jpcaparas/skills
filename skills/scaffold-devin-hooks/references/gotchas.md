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

## 7. Claude config may be inherited, but it is not this scaffold's target

Devin documents that it can load Claude hook config when `read_config_from.claude` is enabled. Inspect inherited Claude hooks when debugging duplicates, but generated project hooks from this skill belong in `.devin/hooks.v1.json`.

## 8. Prompt hooks exist, but this scaffold generates command hooks

Devin documents `command` and `prompt` hook types. This scaffold is bash-first because it needs deterministic repo-owned scripts, merge behavior, and exit-code-2 blocking. Add prompt hooks manually only when the policy truly needs an LLM evaluation.

## 9. Relative commands depend on the hook process cwd

Use `$DEVIN_PROJECT_DIR` for generated command paths. It is documented as the project root environment variable and avoids surprises when Devin starts from a nested working directory.
