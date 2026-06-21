# Agent Hooks

Shared repo-owned hook behavior for Claude Code, Codex, Devin CLI, OpenCode, and GitHub Copilot.

## Layout

- `hooks/<event>/script.sh` is the shared editable behavior for an event.
- `hooks/<event>/<harness>.sh` is a thin adapter invoked by that harness config.
- `hooks/<event>/<harness>.json` stores scripts and commands from the plan.
- `hooks/lib/` stores shared runtime helpers and harness output helpers.
- `hooks/.state/<harness>/` stores generated config fragments and manifests.

## Harness Config

- Claude Code: `.claude/settings.json`
- Codex: `.codex/hooks.json`
- Devin CLI: `.devin/hooks.v1.json`
- OpenCode: `opencode.json` loads `opencode-froggy`, with hooks in `.opencode/hook/hooks.md`

## Event Adapters

- `hooks/config-change/claude.json`
- `hooks/config-change/claude.sh`
- `hooks/config-change/script.sh`
- `hooks/cwd-changed/claude.json`
- `hooks/cwd-changed/claude.sh`
- `hooks/cwd-changed/script.sh`
- `hooks/elicitation-result/claude.json`
- `hooks/elicitation-result/claude.sh`
- `hooks/elicitation-result/script.sh`
- `hooks/elicitation/claude.json`
- `hooks/elicitation/claude.sh`
- `hooks/elicitation/script.sh`
- `hooks/file-changed/claude.json`
- `hooks/file-changed/claude.sh`
- `hooks/file-changed/script.sh`
- `hooks/instructions-loaded/claude.json`
- `hooks/instructions-loaded/claude.sh`
- `hooks/instructions-loaded/script.sh`
- `hooks/message-display/claude.json`
- `hooks/message-display/claude.sh`
- `hooks/message-display/script.sh`
- `hooks/notification/claude.json`
- `hooks/notification/claude.sh`
- `hooks/notification/script.sh`
- `hooks/permission-denied/claude.json`
- `hooks/permission-denied/claude.sh`
- `hooks/permission-denied/script.sh`
- `hooks/permission-request/claude.json`
- `hooks/permission-request/claude.sh`
- `hooks/permission-request/codex.json`
- `hooks/permission-request/codex.sh`
- `hooks/permission-request/devin.json`
- `hooks/permission-request/devin.sh`
- `hooks/permission-request/script.sh`
- `hooks/post-compact/claude.json`
- `hooks/post-compact/claude.sh`
- `hooks/post-compact/codex.json`
- `hooks/post-compact/codex.sh`
- `hooks/post-compact/script.sh`
- `hooks/post-compaction/devin.json`
- `hooks/post-compaction/devin.sh`
- `hooks/post-compaction/script.sh`
- `hooks/post-tool-batch/claude.json`
- `hooks/post-tool-batch/claude.sh`
- `hooks/post-tool-batch/script.sh`
- `hooks/post-tool-use-failure/claude.json`
- `hooks/post-tool-use-failure/claude.sh`
- `hooks/post-tool-use-failure/script.sh`
- `hooks/post-tool-use/claude.json`
- `hooks/post-tool-use/claude.sh`
- `hooks/post-tool-use/codex.json`
- `hooks/post-tool-use/codex.sh`
- `hooks/post-tool-use/devin.json`
- `hooks/post-tool-use/devin.sh`
- `hooks/post-tool-use/script.sh`
- `hooks/pre-compact/claude.json`
- `hooks/pre-compact/claude.sh`
- `hooks/pre-compact/codex.json`
- `hooks/pre-compact/codex.sh`
- `hooks/pre-compact/script.sh`
- `hooks/pre-tool-use/claude.json`
- `hooks/pre-tool-use/claude.sh`
- `hooks/pre-tool-use/codex.json`
- `hooks/pre-tool-use/codex.sh`
- `hooks/pre-tool-use/devin.json`
- `hooks/pre-tool-use/devin.sh`
- `hooks/pre-tool-use/script.sh`
- `hooks/session-end/claude.json`
- `hooks/session-end/claude.sh`
- `hooks/session-end/devin.json`
- `hooks/session-end/devin.sh`
- `hooks/session-end/script.sh`
- `hooks/session-start/claude.json`
- `hooks/session-start/claude.sh`
- `hooks/session-start/codex.json`
- `hooks/session-start/codex.sh`
- `hooks/session-start/devin.json`
- `hooks/session-start/devin.sh`
- `hooks/session-start/script.sh`
- `hooks/setup/claude.json`
- `hooks/setup/claude.sh`
- `hooks/setup/script.sh`
- `hooks/stop-failure/claude.json`
- `hooks/stop-failure/claude.sh`
- `hooks/stop-failure/script.sh`
- `hooks/stop/claude.json`
- `hooks/stop/claude.sh`
- `hooks/stop/codex.json`
- `hooks/stop/codex.sh`
- `hooks/stop/devin.json`
- `hooks/stop/devin.sh`
- `hooks/stop/script.sh`
- `hooks/subagent-start/claude.json`
- `hooks/subagent-start/claude.sh`
- `hooks/subagent-start/codex.json`
- `hooks/subagent-start/codex.sh`
- `hooks/subagent-start/script.sh`
- `hooks/subagent-stop/claude.json`
- `hooks/subagent-stop/claude.sh`
- `hooks/subagent-stop/codex.json`
- `hooks/subagent-stop/codex.sh`
- `hooks/subagent-stop/script.sh`
- `hooks/task-completed/claude.json`
- `hooks/task-completed/claude.sh`
- `hooks/task-completed/script.sh`
- `hooks/task-created/claude.json`
- `hooks/task-created/claude.sh`
- `hooks/task-created/script.sh`
- `hooks/teammate-idle/claude.json`
- `hooks/teammate-idle/claude.sh`
- `hooks/teammate-idle/script.sh`
- `hooks/user-prompt-expansion/claude.json`
- `hooks/user-prompt-expansion/claude.sh`
- `hooks/user-prompt-expansion/script.sh`
- `hooks/user-prompt-submit/claude.json`
- `hooks/user-prompt-submit/claude.sh`
- `hooks/user-prompt-submit/codex.json`
- `hooks/user-prompt-submit/codex.sh`
- `hooks/user-prompt-submit/devin.json`
- `hooks/user-prompt-submit/devin.sh`
- `hooks/user-prompt-submit/script.sh`
- `hooks/worktree-create/claude.json`
- `hooks/worktree-create/claude.sh`
- `hooks/worktree-create/script.sh`
- `hooks/worktree-remove/claude.json`
- `hooks/worktree-remove/claude.sh`
- `hooks/worktree-remove/script.sh`

## Maintenance

The managed manifest at `hooks/.state/scaffold-hooks/manifest.json` records scaffold skill provenance, generator hashes, the selected plan hash, mode, and harness set.

Re-run `/scaffold-hooks` or `scripts/scaffold_all_hooks.sh` from the installed skill to refresh harness adapters. Keep project-specific policy in repo-owned scripts and call those scripts from the plan.
