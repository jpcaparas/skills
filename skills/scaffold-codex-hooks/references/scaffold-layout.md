# Scaffold Layout

## Managed Target Layout

```text
.codex/
├── config.toml                 # Optional, when feature_scope = project
├── hooks.json                  # Shared hook config for this project
└── hooks/
    ├── README.md               # Generated event map and management notes
    └── generated/
        ├── manifest.json       # Snapshot of the scaffold inputs used
        ├── hooks.generated.json # Managed fragment merged into hooks.json
        ├── lib/
        │   └── common.sh       # Helper functions for generated stubs
        └── events/
            ├── session_start.sh
            ├── pre_tool_use.sh
            ├── post_tool_use.sh
            ├── user_prompt_submit.sh
            └── stop.sh
```

Every current official event gets a script stub. Only enabled events are wired into `.codex/hooks.json`.

## Why This Layout

- The event coverage is complete and obvious.
- The managed folder is easy to replace without deleting unrelated custom hooks.
- The top-level `hooks.json` stays human-readable.
- The generated fragment can be rebuilt deterministically.
- The README gives the target project a stable event map.

## Plan File Shape

Use `templates/hook-plan.example.json` as the starting point.

Top-level fields:

- `hooks_target`
- `managed_root`
- `feature_scope`
- `mode`
- `enabled_events`

Each enabled event entry can carry:

- `name`
- `matcher`
- `timeout`
- `status_message`
- `notes`

Keep one managed matcher group per enabled event entry. If you need multiple matcher groups for the same event, extend the plan format first instead of improvising inside the scaffold script.
