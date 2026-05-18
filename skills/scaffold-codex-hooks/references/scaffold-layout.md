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
            ├── permission_request.sh
            ├── post_tool_use.sh
            ├── pre_compact.sh
            ├── post_compact.sh
            ├── user_prompt_submit.sh
            └── stop.sh
```

Every current official event gets a script stub. Only enabled events are wired into `.codex/hooks.json`.

## Event Script Anatomy

Generated event scripts are intentionally plain bash with one obvious edit point:

```text
bootstrap imports ../lib/common.sh
main() reads the hook JSON payload from stdin into HOOK_INPUT
run_configured_commands() runs any repo commands listed for the event
handle_event() contains the project-specific hook logic
```

Keep `main()` boring. Add project checks, policy gates, logging, or structured hook output inside `handle_event()`. Shared helpers such as `hook_json`, `run_configured_commands`, `emit_additional_context`, `deny_pre_tool_use`, and `block_with_reason` live in `lib/common.sh` and are commented where they are defined.

## Existing Project Commands

Many useful hooks do not need custom logic. They need to run commands the project already owns, such as a documented quality gate, formatter, test target, task-runner recipe, or local script. Model that as data in the plan instead of hard-coding a language or package manager into the generated bash:

```json
{
  "name": "Stop",
  "timeout": 120,
  "status_message": "Running project quality gate",
  "commands": [
    {
      "label": "repo quality gate",
      "command": "<existing repo command>",
      "cwd": ".",
      "notes": "Use the command already documented by this repository."
    }
  ]
}
```

The scaffold copies those command entries into the event script as JSON. The script runs them before any custom `handle_event()` logic and converts failures into the safest output shape for the event. Keep command discovery language-agnostic: audit actual repo files, docs, CI, task runners, and existing scripts, then put the real command in the plan.

## Why This Layout

- The event coverage is complete and obvious.
- The managed folder is easy to replace without deleting unrelated custom hooks.
- The top-level `hooks.json` stays human-readable.
- The generated fragment can be rebuilt deterministically.
- The README gives the target project a stable event map.
- The generated scripts are modular enough for future humans and agents to extend without reverse-engineering hook I/O or language-specific command wrappers first.

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
- `commands`
- `notes`

Keep one managed matcher group per enabled event entry. If you need multiple matcher groups for the same event, extend the plan format first instead of improvising inside the scaffold script.
