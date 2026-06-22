# Reusable Scripts

Use this when a hook behavior should survive a move between Codex, Claude Code, OpenCode, Git hooks, GitHub Actions, or a local terminal.

## Placement Pattern

Keep project behavior in repo-owned scripts under a stable project directory:

```text
scripts/
├── agent-session-context.sh   # shared context producer
├── agent-stop-checks.sh       # shared checks with a harness mode argument
├── codex-stop-checks.sh       # optional thin Codex adapter
├── claude-stop-checks.sh      # optional thin Claude adapter
└── opencode-stop-checks.sh    # optional thin OpenCode adapter
```

Shared `hooks/<event>/script.sh` files should stay thin. They read the active harness payload, load plan data from `hooks/<event>/codex.json`, call shared scripts from the plan's `scripts` array, and delegate Codex-specific output to `hooks/lib/codex.sh`.

## Script Rules

- Resolve the repo root inside shared scripts, usually with `git rev-parse --show-toplevel`.
- Accept a harness or mode argument when output protocols differ, for example `agent-stop-checks.sh codex`.
- For `SessionStart` context, use `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}`; Claude Code, Codex, and Devin all accept this shared shape.
- Keep toolchain commands in shared scripts or existing repo task runners, not inside managed hook stubs.
- Make shared scripts callable by humans and CI: `bash <project>/scripts/agent-stop-checks.sh codex`.
- Use adapter scripts only when Codex's JSON output contract differs enough to justify them.

## Plan Example

```json
{
  "name": "Stop",
  "timeout": 600,
  "status_message": "Running shared stop checks",
  "scripts": [
    {
      "label": "shared stop checks",
      "path": "scripts/agent-stop-checks.sh",
      "args": ["codex"],
      "cwd": "."
    }
  ],
  "commands": []
}
```

Read `references/scaffold-layout.md` for how the managed bash stubs execute these entries.
