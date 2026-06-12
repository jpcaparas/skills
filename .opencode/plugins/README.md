# OpenCode Hooks

Project-local OpenCode hook plugin scaffold for this repo.

## Active Plugins

- `skills_repo_stop_check.ts` - OpenCode lifecycle adapter into shared repository stop checks.

## Behavior

- `session.created` injects no-reply context from `hooks/opencode-session-created/opencode.sh`.
- `session.idle` runs `hooks/opencode-session-idle/opencode.sh` for Skills repository stop checks.
- Meaningful background work uses TUI toasts for start, success, warning, and error states.
- First failure gets one automatic repair prompt; persistent failure is reported with `noReply: true`.

## Notes

- OpenCode hooks are plugins loaded from the configured plugin directory.
- This setup keeps only active plugin behavior and does not generate a full hook-surface catalog.
- Lifecycle/action plugins resolve repo scripts from the active OpenCode project/worktree/directory context before falling back to the plugin path.
- `client.app.log()` is for diagnostics; `client.tui.showToast()` is the user-visible feedback path.
- Config-dir dependencies and lockfiles are only needed when plugin code imports external packages.

## Sources

- https://opencode.ai/docs/plugins/
- https://opencode.ai/docs/config/
- https://opencode.ai/docs/sdk
- https://opencode.ai/docs/custom-tools
- https://opencode.ai/docs/troubleshooting
