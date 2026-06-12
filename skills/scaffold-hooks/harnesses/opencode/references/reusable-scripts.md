# Reusable Scripts

Use this when OpenCode plugin behavior should share project logic with Codex, Claude Code, Devin, Git hooks, GitHub Actions, or a local terminal.

## Placement Pattern

Keep project behavior in repo-owned scripts under a stable project directory:

```text
scripts/
├── agent-session-context.sh   # shared context producer
├── agent-stop-checks.sh       # shared checks with a harness mode argument
├── opencode-stop-checks.sh    # optional thin OpenCode adapter
├── codex-stop-checks.sh       # optional thin Codex adapter
└── claude-stop-checks.sh      # optional thin Claude adapter
```

Generated OpenCode plugins should orchestrate lifecycle, TUI feedback, logging, and one controlled repair prompt. Project logic belongs in `hooks/opencode-session-created/script.sh`, `hooks/opencode-session-idle/script.sh`, or repo-owned delegate scripts those adapters call.

## Script Rules

- Resolve the repo root inside shared scripts, usually with `git rev-parse --show-toplevel`.
- Accept a harness or mode argument when output protocols differ, for example `agent-stop-checks.sh opencode`.
- Keep toolchain commands in shared scripts or existing repo task runners, not inside generated plugin bodies.
- Make shared scripts callable by humans and CI: `bash <project>/scripts/agent-stop-checks.sh opencode`.
- Use adapter scripts only when OpenCode's prompt/repair flow needs output that differs from Codex or Claude Code.

## Plan Example

```json
{
  "name": "project-session-lifecycle",
  "pattern": "lifecycle-action",
  "filename": "opencode_hook_project_session_lifecycle.ts",
  "surfaces": ["event"],
  "context_script": "hooks/opencode-session-created/opencode.sh",
  "action_script": "hooks/opencode-session-idle/opencode.sh",
  "context_delegate_script": "scripts/agent-session-context.sh",
  "action_delegate_script": "scripts/opencode-stop-checks.sh",
  "action_label": "Project validation",
  "service": "project-opencode-hooks"
}
```

The lifecycle template resolves the active repo from OpenCode's plugin context (`worktree`, `directory`, or project fields) before falling back to the plugin directory, so the same plugin shape works for project-local and global scopes.
