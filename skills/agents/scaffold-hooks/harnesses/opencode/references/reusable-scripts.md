# Reusable Scripts

Froggy should call repo-owned scripts instead of embedding validation policy in `hooks.md`.

Recommended scripts:

- `./scripts/agent-session-context.sh` for session baselines and optional context
- `./scripts/validate-project.sh` for generic post-turn validation
- `./scripts/agent-stop-checks.sh` for repository-wide stop checks

Set these environment variables in Froggy bash commands when calling shared scripts:

```bash
AGENT_HOOK_HARNESS=opencode
AGENT_HOOK_PROJECT_ROOT="$OPENCODE_PROJECT_DIR"
AGENT_HOOK_SESSION_ID="$OPENCODE_SESSION_ID"
```

Use the project path argument when the script accepts one:

```bash
bash "$OPENCODE_PROJECT_DIR/scripts/agent-stop-checks.sh" "$OPENCODE_PROJECT_DIR"
```

Froggy already provides JSON context on stdin. If a script needs tool arguments or modified file lists, read stdin with `jq`.

## Exit Codes and Streams

Design reusable scripts so exit code carries control flow and streams carry text:

- Exit `0` for success, including "nothing to do" skips.
- Exit `2` only when the target hook event treats it as a block signal.
- Write diagnostics, failure details, and block reasons to stderr.
- Write successful informational text to stdout only when the harness protocol allows it; otherwise keep successful no-op paths quiet.

For Froggy bash actions, stdout and stderr are both displayed in the session. Do not put successful skip messages on stderr.
