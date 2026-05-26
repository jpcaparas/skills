# OpenCode Plugins

Project-local OpenCode hooks for this repository.

## Active Plugins

- `skills_repo_stop_check.ts`: runs `scripts/agent-stop-checks.sh` on `session.idle`, then prompts one repair pass when the shared stop pipeline exits non-zero.

The validation policy lives in repo-owned scripts so Codex, OpenCode, Git hooks, GitHub Actions, and manual checks use the same path.
