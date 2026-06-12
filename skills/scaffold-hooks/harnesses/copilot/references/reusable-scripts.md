# Reusable Scripts

Use this when a hook behavior should survive a move between Copilot, Devin, Codex, OpenCode, Git hooks, GitHub Actions, or a local terminal.

## Placement Pattern

Keep project behavior in repo-owned scripts under a stable project directory:

```text
scripts/
├── agent-session-context.sh
├── agent-stop-checks.sh
├── copilot-pre-tool-policy.sh
├── devin-stop-checks.sh
├── codex-stop-checks.sh
└── opencode-stop-checks.sh
```

Generated `.github/copilot/hooks/generated/events/*.sh` files should stay thin. They read Copilot's hook payload, call shared scripts from the plan's `scripts` array, and translate failures into Copilot's documented output and exit-code contract.

## Script Rules

- Resolve the repo root inside shared scripts, usually with `git rev-parse --show-toplevel`.
- Accept a harness or mode argument when output protocols differ, for example `agent-stop-checks.sh copilot`.
- Keep toolchain commands in shared scripts or existing repo task runners, not inside generated hook stubs.
- Make shared scripts callable by humans and CI: `bash scripts/agent-stop-checks.sh copilot`.
- Use adapter scripts only when the protocol output differs enough to justify them.
- Send logs to stderr. Reserve stdout for hook decision JSON when the script intentionally controls Copilot.
- Keep cloud-agent-safe scripts short, non-interactive, and network-light.

## Plan Example

```json
{
  "name": "agentStop",
  "timeoutSec": 30,
  "block_on_failure": true,
  "scripts": [
    {
      "label": "shared stop checks",
      "path": "scripts/agent-stop-checks.sh",
      "args": ["copilot"],
      "cwd": "."
    }
  ],
  "commands": []
}
```

Read `references/scaffold-layout.md` for how the generated bash stubs execute these entries.
