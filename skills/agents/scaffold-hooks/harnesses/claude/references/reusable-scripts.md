# Reusable Scripts

Use this when a hook behavior should survive a move between Claude Code, Codex, OpenCode, Git hooks, GitHub Actions, or a local terminal.

## Placement Pattern

Keep project behavior in repo-owned scripts under a stable project directory:

```text
scripts/
├── agent-session-context.sh   # shared context producer
├── agent-stop-checks.sh       # shared checks with a harness mode argument
├── claude-stop-checks.sh      # optional thin Claude adapter
├── codex-stop-checks.sh       # optional thin Codex adapter
└── opencode-stop-checks.sh    # optional thin OpenCode adapter
```

Shared `hooks/<event>/script.sh` files should stay thin. They read the active harness payload, load plan data from `hooks/<event>/claude.json`, call shared scripts from the plan's `scripts` array, and delegate Claude-specific output to `hooks/lib/claude.sh`.

## Script Rules

- Resolve the repo root inside shared scripts, usually with `git rev-parse --show-toplevel`.
- Accept a harness or mode argument when output protocols differ, for example `agent-stop-checks.sh claude`.
- For `SessionStart` context, use `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}` for Claude, Codex, and Devin. Claude Code accepts this shared shape, so there is no need for a Claude-only top-level `additionalContext` branch.
- Keep toolchain commands in shared scripts or existing repo task runners, not inside managed hook stubs.
- Make shared scripts callable by humans and CI: `bash <project>/scripts/agent-stop-checks.sh claude`.
- Use adapter scripts only when the protocol output differs enough to justify them.

## Plan Example

```json
{
  "name": "Stop",
  "async": false,
  "timeout": 600,
  "scripts": [
    {
      "label": "shared stop checks",
      "path": "scripts/agent-stop-checks.sh",
      "args": ["claude"],
      "cwd": "."
    }
  ],
  "commands": []
}
```

Read `references/scaffold-layout.md` for how the managed bash stubs execute these entries.
