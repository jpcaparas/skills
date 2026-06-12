# Reusable Scripts

Use this when a hook behavior should survive a move between Devin, Codex, OpenCode, Git hooks, GitHub Actions, or a local terminal.

## Placement Pattern

Keep project behavior in repo-owned scripts under a stable project directory:

```text
scripts/
├── agent-session-context.sh   # shared context producer
├── agent-stop-checks.sh       # shared checks with a harness mode argument
├── devin-stop-checks.sh       # optional thin Devin adapter
├── codex-stop-checks.sh       # optional thin Codex adapter
└── opencode-stop-checks.sh    # optional thin OpenCode adapter
```

Shared `hooks/<event>/script.sh` files should stay thin. They read the active harness payload, load plan data from `hooks/<event>/devin.json`, call shared scripts from the plan's `scripts` array, and delegate Devin-specific output and exit-code handling to `hooks/lib/devin.sh`.

## Script Rules

- Resolve the repo root inside shared scripts, usually with `git rev-parse --show-toplevel`.
- Accept a harness or mode argument when output protocols differ, for example `agent-stop-checks.sh devin`.
- Keep toolchain commands in shared scripts or existing repo task runners, not inside managed hook stubs.
- Make shared scripts callable by humans and CI: `bash <project>/scripts/agent-stop-checks.sh devin`.
- Use adapter scripts only when the protocol output differs enough to justify them.
- Send logs to stderr. Reserve stdout for hook decision JSON when the script intentionally controls Devin.

## Plan Example

```json
{
  "name": "Stop",
  "timeout": 600,
  "block_on_failure": true,
  "scripts": [
    {
      "label": "shared stop checks",
      "path": "scripts/agent-stop-checks.sh",
      "args": ["devin"],
      "cwd": "."
    }
  ],
  "commands": []
}
```

Read `references/scaffold-layout.md` for how the managed bash stubs execute these entries.
