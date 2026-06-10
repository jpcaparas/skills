# Scaffold Layout

The target project scaffold is deterministic on purpose. The plan decides what is enabled, but the shape stays fixed.

## Managed Target Layout

```text
.devin/
├── hooks.v1.json
└── hooks/
    ├── README.md
    └── generated/
        ├── manifest.json
        ├── hooks.generated.json
        ├── lib/
        │   └── common.sh
        └── events/
            ├── pre-tool-use.sh
            ├── post-tool-use.sh
            ├── permission-request.sh
            ├── user-prompt-submit.sh
            ├── stop.sh
            ├── post-compaction.sh
            ├── session-start.sh
            └── session-end.sh
```

Every documented Devin lifecycle event gets a script stub. Only enabled events are registered in `.devin/hooks.v1.json`.

## Event Script Anatomy

Generated event scripts are intentionally plain bash with one obvious edit point:

```text
bootstrap imports ../lib/common.sh
main() reads Devin's JSON payload from stdin into HOOK_INPUT
run_configured_scripts() delegates to repo-owned scripts listed for the event
run_configured_commands() runs any repo commands listed in the plan
handle_event() contains the project-specific hook logic
```

Keep `main()` boring. Add project checks, policy gates, logging, or structured hook output inside `handle_event()`.

## Blocking Behavior

Use `block_on_failure: true` when a configured script or command failure must deny the action. The generated hook then prints a JSON block decision and exits `2`.

Use `block_on_failure: false` for observer hooks where failures should be logged but not deny the current action.

## Reusable Project Scripts

Prefer repo-owned scripts for behavior that may need to move between Devin, Codex, OpenCode, Git hooks, GitHub Actions, or a local shell.

Plan shape:

```json
{
  "name": "Stop",
  "timeout": 120,
  "block_on_failure": true,
  "scripts": [
    {
      "label": "shared stop checks",
      "path": "scripts/agent-stop-checks.sh",
      "args": ["devin"],
      "cwd": ".",
      "notes": "Script is repo-owned and can also be called by CI or other agent adapters."
    }
  ],
  "commands": []
}
```

Resolve `path` relative to the target project root. Keep the shared script path-agnostic by discovering the repo root at runtime and by accepting a harness/mode argument when output protocols differ.

## Existing Project Commands

Use `commands` for stable existing command entry points, such as a documented quality gate, formatter, test target, task-runner recipe, or package script.

```json
{
  "name": "PostToolUse",
  "matcher": "^(edit|exec)$",
  "timeout": 120,
  "block_on_failure": false,
  "scripts": [],
  "commands": [
    {
      "label": "repo quality signal",
      "command": "<existing repo command>",
      "cwd": ".",
      "notes": "Use the command already documented by this repository."
    }
  ]
}
```

The scaffold copies command entries into the event script as JSON. The script runs them before custom `handle_event()` logic.

## Plan File Shape

Use a small JSON file like `templates/hook-plan.example.json`:

```json
{
  "hooks_target": ".devin/hooks.v1.json",
  "managed_root": ".devin/hooks/generated",
  "mode": "additive",
  "enabled_events": [
    {
      "name": "PreToolUse",
      "matcher": "^exec$",
      "timeout": 30,
      "block_on_failure": true,
      "scripts": [],
      "commands": [],
      "notes": "Use this for hard policy and safety gates."
    }
  ]
}
```

The scaffold script treats every event not listed in `enabled_events` as disabled but still creates its stub script.

## Hooks Target Rules

- Prefer `.devin/hooks.v1.json`.
- Do not place generated hooks under `.devin/config.json` unless the user explicitly asks.
- Do not place generated hooks under Claude config paths.
- If an existing `.devin/hooks.v1.json` already owns project hooks, update that file additively unless there is a strong reason to overhaul the managed layer.

## See Also

- `references/hook-events.md`
- `references/merge-strategy.md`
- `references/reusable-scripts.md`
