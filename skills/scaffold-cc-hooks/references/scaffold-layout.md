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

## Why This Layout

- The event coverage is complete and obvious.
- The managed folder is easy to replace without deleting unrelated custom hooks.
- The target project gets a readable `README.md` next to the hooks.
- Re-runs can refresh the managed layer while preserving non-managed scripts.

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

