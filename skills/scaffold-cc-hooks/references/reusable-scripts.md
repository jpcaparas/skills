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

Generated `.claude/hooks/generated/events/*.sh` files should stay thin. They read Claude's hook payload, call shared scripts from the plan's `scripts` array, and translate failures into the right Claude Code output shape.

## Script Rules

- Resolve the repo root inside shared scripts, usually with `git rev-parse --show-toplevel`.
- Accept a harness or mode argument when output protocols differ, for example `agent-stop-checks.sh claude`.
- Keep toolchain commands in shared scripts or existing repo task runners, not inside generated hook stubs.
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

Read `references/scaffold-layout.md` for how the generated bash stubs execute these entries.
