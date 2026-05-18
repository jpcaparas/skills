# Scaffold Layout

The target project scaffold is deterministic on purpose. The plan decides what is enabled, but the shape stays fixed.

## Managed Target Layout

```text
.claude/
├── settings.json or settings.local.json
└── hooks/
    ├── README.md
    └── generated/
        ├── manifest.json
        ├── settings.generated.json
        ├── lib/
        │   └── common.sh
        └── events/
            ├── session-start.sh
            ├── instructions-loaded.sh
            ├── user-prompt-submit.sh
            ├── pre-tool-use.sh
            ├── permission-request.sh
            ├── permission-denied.sh
            ├── post-tool-use.sh
            ├── post-tool-use-failure.sh
            ├── notification.sh
            ├── subagent-start.sh
            ├── subagent-stop.sh
            ├── task-created.sh
            ├── task-completed.sh
            ├── stop.sh
            ├── stop-failure.sh
            ├── teammate-idle.sh
            ├── config-change.sh
            ├── cwd-changed.sh
            ├── file-changed.sh
            ├── worktree-create.sh
            ├── worktree-remove.sh
            ├── pre-compact.sh
            ├── post-compact.sh
            ├── session-end.sh
            ├── elicitation.sh
            └── elicitation-result.sh
```

Every official event gets a script stub. Only enabled events are registered in the settings file.

## Event Script Anatomy

Generated event scripts are intentionally plain bash with one obvious edit point:

```text
bootstrap imports ../lib/common.sh
main() reads the hook JSON payload from stdin into HOOK_INPUT
run_configured_commands() runs any repo commands listed for the event
handle_event() contains the project-specific hook logic
```

Keep `main()` boring. Add project checks, policy gates, logging, or structured hook output inside `handle_event()`. Shared helpers such as `hook_json`, `run_configured_commands`, `write_system_message`, and `write_additional_context` live in `lib/common.sh` and are commented where they are defined.

## Existing Project Commands

Many useful hooks do not need custom logic. They need to run commands the project already owns, such as a documented quality gate, formatter, test target, task-runner recipe, or local script. Model that as data in the plan instead of hard-coding a language or package manager into the generated bash:

```json
{
  "name": "Stop",
  "async": false,
  "timeout": 120,
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
- The target project gets a readable `README.md` next to the hooks.
- Re-runs can refresh the managed layer while preserving non-managed scripts.
- The generated scripts are modular enough for future humans and agents to extend without reverse-engineering hook I/O or language-specific command wrappers first.

## Plan File Shape

Use a small JSON file like `templates/hook-plan.example.json`:

```json
{
  "settings_target": ".claude/settings.json",
  "managed_root": ".claude/hooks/generated",
  "mode": "additive",
  "enabled_events": [
    {
      "name": "PreToolUse",
      "matcher": "Edit|Write|MultiEdit|Bash",
      "async": false,
      "timeout": 30,
      "if": "",
      "commands": [],
      "notes": "Use this for hard safety and policy gates."
    }
  ]
}
```

The scaffold script treats every event not listed in `enabled_events` as disabled but still creates its stub script.

## Settings Target Rules

- Prefer `.claude/settings.json` for shared project policy.
- Prefer `.claude/settings.local.json` only when the behavior is developer-specific or the repo already uses that pattern.
- If an existing settings file already owns project hooks, update that file unless there is a strong reason to move.
