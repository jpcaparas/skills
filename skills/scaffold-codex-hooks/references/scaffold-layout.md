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
            ├── subagent_start.sh
            ├── pre_tool_use.sh
            ├── permission_request.sh
            ├── post_tool_use.sh
            ├── pre_compact.sh
            ├── post_compact.sh
            ├── user_prompt_submit.sh
            ├── subagent_stop.sh
            └── stop.sh
```

Every current official event gets a script stub. Only enabled events are wired into `.codex/hooks.json`.

## Event Script Anatomy

Generated event scripts are intentionally plain bash with one obvious edit point:

```text
bootstrap imports ../lib/common.sh
main() reads the hook JSON payload from stdin into HOOK_INPUT
run_configured_scripts() delegates to repo-owned scripts listed for the event
run_configured_commands() runs any repo commands listed for the event
handle_event() contains the project-specific hook logic
```

Keep `main()` boring. Add project checks, policy gates, logging, or structured hook output inside `handle_event()`. Shared helpers such as `hook_json`, `run_configured_scripts`, `run_configured_commands`, `emit_additional_context`, `deny_pre_tool_use`, and `block_with_reason` live in `lib/common.sh` and are commented where they are defined.

## Reusable Project Scripts

Prefer repo-owned scripts for behavior that may need to move between Codex, Claude Code, OpenCode, Git hooks, GitHub Actions, or a local shell. Keep generated Codex hook files as adapters that read hook input and translate failures into Codex's output contract.

Plan shape:

```json
{
  "name": "Stop",
  "timeout": 120,
  "status_message": "Running shared stop checks",
  "scripts": [
    {
      "label": "shared stop checks",
      "path": "scripts/agent-stop-checks.sh",
      "args": ["codex"],
      "cwd": ".",
      "notes": "Script is repo-owned and can also be called by CI or other agent adapters."
    }
  ],
  "commands": []
}
```

Resolve `path` relative to the target project root. Keep shared scripts path-agnostic by discovering the repo root at runtime, for example with `git rev-parse --show-toplevel`, and by accepting a harness/mode argument when output protocols differ.

## Existing Project Commands

Use `commands` for existing command entry points that are already stable and reusable, such as a documented quality gate, formatter, test target, task-runner recipe, or package script. Use `scripts` when you need a small repo-owned adapter or a shared shell script that other harnesses can call directly.

```json
{
  "name": "Stop",
  "timeout": 120,
  "status_message": "Running project quality gate",
  "scripts": [],
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
- `scripts`
- `commands`
- `notes`

Keep one managed matcher group per enabled event entry. If you need multiple matcher groups for the same event, extend the plan format first instead of improvising inside the scaffold script.
