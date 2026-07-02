# Scaffold Layout

## Default Target Layout

Codex config stays in `.codex/hooks.json`, but executable hook behavior lives in a shared repo-owned `hooks/` tree:

```text
.codex/
└── hooks.json                 # Codex hook config; points at hooks/<event>/codex.sh

hooks/
├── README.md                  # Generated event and adapter map
├── lib/
│   ├── agent-hook-runtime.sh  # Harness-neutral input/config/command helpers
│   └── codex.sh               # Codex output and decision helpers
├── .state/
│   └── codex/
│       ├── manifest.json      # Snapshot of manifest, feature state, and enabled plan entries
│       └── hooks.json         # Fragment merged into .codex/hooks.json
└── session-start/
    ├── script.sh              # Shared editable event behavior
    ├── codex.sh               # Thin Codex adapter invoked by hooks.json
    └── codex.json             # Codex-specific plan data for this event
```

Every official Codex event gets the same `hooks/<event>/script.sh`, `codex.sh`, and `codex.json` shape. Only enabled events are wired into `.codex/hooks.json`.

## Ports And Adapters

- `hooks/<event>/script.sh` is the port: shared project behavior that can be reused by Codex, Claude Code, Devin, OpenCode, CI, or a human shell.
- `hooks/<event>/codex.sh` is the adapter: it sets `AGENT_HOOK_HARNESS=codex`, sets `AGENT_HOOK_EVENT`, and runs `script.sh` through Bash so hooks still work on `noexec` temp or workspace mounts.
- `hooks/<event>/codex.json` is adapter data: scripts, commands, and other plan details for Codex.
- `hooks/lib/codex.sh` translates shared failures into Codex's JSON output contract.

## Plan File Shape

Use `templates/hook-plan.example.json` as the starting point:

```json
{
  "hooks_target": ".codex/hooks.json",
  "managed_root": "hooks",
  "feature_scope": "project",
  "mode": "additive",
  "enabled_events": [
    {
      "name": "SessionStart",
      "matcher": "startup",
      "scripts": [
        {
          "label": "session context",
          "path": "scripts/agent-session-context.sh",
          "args": ["codex"],
          "cwd": "."
        }
      ]
    }
  ]
}
```

Keep project-specific judgment in the plan. The scaffold remains deterministic by rendering adapter data from the plan and leaving shared behavior in `script.sh`.
