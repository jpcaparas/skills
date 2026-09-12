# Scaffold Layout

## Default Target Layout

Claude Code config stays in `.claude/settings.json`, but executable hook behavior lives in a shared repo-owned `hooks/` tree:

```text
.claude/
└── settings.json              # Claude Code hook config; points at hooks/<event>/claude.sh

hooks/
├── README.md                  # Generated event and adapter map
├── lib/
│   ├── agent-hook-runtime.sh  # Harness-neutral input/config/command helpers
│   └── claude.sh              # Claude Code output and decision helpers
├── .state/
│   └── claude/
│       ├── manifest.json      # Snapshot of manifest and enabled plan entries
│       └── settings.json      # Fragment merged into .claude/settings.json
└── stop/
    ├── script.sh              # Shared editable event behavior
    ├── claude.sh              # Thin Claude adapter invoked by settings.json
    └── claude.json            # Claude-specific plan data for this event
```

Every official Claude Code event gets the same `hooks/<event>/script.sh`, `claude.sh`, and `claude.json` shape. Only enabled events are wired into `.claude/settings.json`.

## Ports And Adapters

- `hooks/<event>/script.sh` is the port: shared project behavior that can be reused by Claude Code, Codex, Devin, OpenCode, CI, or a human shell.
- `hooks/<event>/claude.sh` is the adapter: it sets `AGENT_HOOK_HARNESS=claude`, sets `AGENT_HOOK_EVENT`, and runs `script.sh` through Bash so hooks still work on `noexec` temp or workspace mounts.
- `hooks/<event>/claude.json` is adapter data: scripts, commands, and other plan details for Claude.
- `hooks/lib/claude.sh` translates shared failures into Claude Code's JSON output contract.

## Plan File Shape

Use `templates/hook-plan.example.json` as the starting point:

```json
{
  "settings_target": ".claude/settings.json",
  "managed_root": "hooks",
  "mode": "additive",
  "enabled_events": [
    {
      "name": "Stop",
      "scripts": [
        {
          "label": "stop checks",
          "path": "scripts/agent-stop-checks.sh",
          "args": ["claude"],
          "cwd": "."
        }
      ]
    }
  ]
}
```

Keep project-specific judgment in the plan. The scaffold remains deterministic by rendering adapter data from the plan and leaving shared behavior in `script.sh`.
