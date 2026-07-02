# Scaffold Layout

## Default Target Layout

Devin config stays in `.devin/hooks.v1.json`, but executable hook behavior lives in a shared repo-owned `hooks/` tree:

```text
.devin/
└── hooks.v1.json              # Devin hook config; points at hooks/<event>/devin.sh

hooks/
├── README.md                  # Generated event and adapter map
├── lib/
│   ├── agent-hook-runtime.sh  # Harness-neutral input/config/command helpers
│   └── devin.sh               # Devin decision and exit-code helpers
├── .state/
│   └── devin/
│       ├── manifest.json      # Snapshot of manifest and enabled plan entries
│       └── hooks.v1.json      # Fragment merged into .devin/hooks.v1.json
└── stop/
    ├── script.sh              # Shared editable event behavior
    ├── devin.sh               # Thin Devin adapter invoked by hooks.v1.json
    └── devin.json             # Devin-specific plan data for this event
```

Every documented Devin lifecycle event gets the same `hooks/<event>/script.sh`, `devin.sh`, and `devin.json` shape. Only enabled events are wired into `.devin/hooks.v1.json`.

## Ports And Adapters

- `hooks/<event>/script.sh` is the port: shared project behavior that can be reused by Devin, Claude Code, Codex, OpenCode, CI, or a human shell.
- `hooks/<event>/devin.sh` is the adapter: it sets `AGENT_HOOK_HARNESS=devin`, sets `AGENT_HOOK_EVENT`, and runs `script.sh` through Bash so hooks still work on `noexec` temp or workspace mounts.
- `hooks/<event>/devin.json` is adapter data: scripts, commands, and `block_on_failure` for Devin.
- `hooks/lib/devin.sh` translates shared failures into Devin's JSON decision and exit-code-2 contract.

## Plan File Shape

Use `templates/hook-plan.example.json` as the starting point:

```json
{
  "hooks_target": ".devin/hooks.v1.json",
  "managed_root": "hooks",
  "mode": "additive",
  "enabled_events": [
    {
      "name": "Stop",
      "block_on_failure": true,
      "scripts": [
        {
          "label": "stop checks",
          "path": "scripts/agent-stop-checks.sh",
          "args": ["devin"],
          "cwd": "."
        }
      ]
    }
  ]
}
```

Keep project-specific judgment in the plan. The scaffold remains deterministic by rendering adapter data from the plan and leaving shared behavior in `script.sh`.
