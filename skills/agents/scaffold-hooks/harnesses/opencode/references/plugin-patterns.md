# Froggy Hook Patterns

## Session Baseline

Use `session.created` to call a repo-owned context script when it exists:

```json
{
  "event": "session.created",
  "conditions": ["isMainSession"],
  "actions": [
    {
      "bash": {
        "command": "if [ -f \"$OPENCODE_PROJECT_DIR/scripts/agent-session-context.sh\" ]; then AGENT_HOOK_HARNESS=opencode AGENT_HOOK_PROJECT_ROOT=\"$OPENCODE_PROJECT_DIR\" AGENT_HOOK_SESSION_ID=\"$OPENCODE_SESSION_ID\" bash \"$OPENCODE_PROJECT_DIR/scripts/agent-session-context.sh\" >/dev/null; fi",
        "timeout": 20000
      }
    }
  ]
}
```

Redirect stdout when the script is only recording baseline state; Froggy sends bash output back to the session.

## Post-Turn Validation

Use `session.idle` for stop-style checks:

```json
{
  "event": "session.idle",
  "conditions": ["isMainSession"],
  "actions": [
    {
      "bash": {
        "command": "if [ -f \"$OPENCODE_PROJECT_DIR/scripts/validate-project.sh\" ]; then AGENT_HOOK_HARNESS=opencode AGENT_HOOK_PROJECT_ROOT=\"$OPENCODE_PROJECT_DIR\" AGENT_HOOK_SESSION_ID=\"$OPENCODE_SESSION_ID\" bash \"$OPENCODE_PROJECT_DIR/scripts/validate-project.sh\" \"$OPENCODE_PROJECT_DIR\"; fi",
        "timeout": 600000
      }
    }
  ]
}
```

For this skills repo, use `./scripts/agent-stop-checks.sh` instead of a generic validate script.

## Guardrails

Use `tool.before.write`, `tool.before.edit`, or `tool.before.*` to block risky operations:

```json
{
  "event": "tool.before.write",
  "actions": [
    {
      "bash": "file=$(cat | jq -r '.tool_args.filePath // .tool_args.file_path // .tool_args.path // \"\"'); case \"$file\" in *.env|*.pem|*.key) echo \"Blocked sensitive file: $file\" >&2; exit 2 ;; esac"
    }
  ]
}
```

## Observers

Use `tool.after.*` or `tool.after.<name>` for logging and non-blocking follow-up. Keep output short because Froggy sends bash results back into the session.
