# Codex Hooks

Managed Codex hook scaffold for this project.

## Managed Paths

- `hooks.json`: `.codex/hooks.json`
- managed root: `.codex/hooks/generated`
- feature scope: project (`.codex/config.toml`)

## Notes

- Current Codex runtime only supports command hooks in practice today.
- `PreToolUse` and `PostToolUse` currently match Bash-only traffic.
- Project-local hooks run alongside any active user-global `~/.codex/hooks.json` handlers.
- Re-run the scaffold when the official docs or schemas change.

## Event Map

| Event | Enabled | Matcher | Timeout | Script | Notes |
|------|---------|---------|---------|--------|-------|
| `SessionStart` | yes | `startup|resume` | `20` | `session_start.sh` | Inject the repository's skill layout and validation rules when a Codex session starts or resumes. |
| `PreToolUse` | yes | `Bash` | `20` | `pre_tool_use.sh` | Block destructive git and shell commands that could wipe local work or the repository. |
| `PostToolUse` | yes | `Bash` | `20` | `post_tool_use.sh` | Add repo-specific reminders after Bash commands that touch skill directories or validation entry points. |
| `UserPromptSubmit` | no | `ignored` | `—` | `user_prompt_submit.sh` | Inject context into user prompts or block a prompt before it is sent. |
| `Stop` | yes | `ignored` | `300` | `stop.sh` | Run the shared validation script before the turn ends so Codex catches the same failures as CI. |

## Sources

- https://developers.openai.com/codex/hooks
- https://developers.openai.com/codex/config-basic
- https://developers.openai.com/codex/config-reference
- https://github.com/openai/codex/tree/main/codex-rs/hooks/schema/generated
