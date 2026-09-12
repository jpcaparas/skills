# Scaffold Layout

The target project scaffold is deterministic on purpose. The plan decides what is enabled, but the shape stays fixed.

## Managed Target Layout

```text
.github/
├── hooks/
│   └── copilot-hooks.json
└── copilot/
    └── hooks/
        ├── README.md
        └── generated/
            ├── manifest.json
            ├── hooks.generated.json
            ├── lib/
            │   └── common.sh
            └── events/
                ├── session-start.sh
                ├── session-end.sh
                ├── user-prompt-submitted.sh
                ├── pre-tool-use.sh
                ├── post-tool-use.sh
                ├── post-tool-use-failure.sh
                ├── agent-stop.sh
                ├── subagent-start.sh
                ├── subagent-stop.sh
                ├── error-occurred.sh
                ├── pre-compact.sh
                ├── permission-request.sh
                └── notification.sh
```

Every documented Copilot hook event gets a script stub. Only enabled events are registered in `.github/hooks/copilot-hooks.json`.

## Event Script Anatomy

Generated event scripts are intentionally plain bash with one obvious edit point:

```text
bootstrap imports ../lib/common.sh
main() reads Copilot's JSON payload from stdin into HOOK_INPUT
run_configured_scripts() delegates to repo-owned scripts listed for the event
run_configured_commands() runs any repo commands listed in the plan
handle_event() contains the project-specific hook logic
```

Keep `main()` boring. Add project checks, policy gates, logging, or structured hook output inside `handle_event()`.

## Blocking Behavior

Use `block_on_failure: true` only when a configured script or command failure must affect agent behavior.

The generated hook translates failures based on the event:

| Event | Generated Blocking Translation |
|-------|--------------------------------|
| `preToolUse` | stdout JSON `permissionDecision: "deny"` and exit `0` |
| `permissionRequest` | stdout JSON `behavior: "deny"` and exit `2` |
| `agentStop`, `subagentStop` | stdout JSON `decision: "block"` and exit `0` |
| `postToolUseFailure` | stdout JSON `additionalContext` and exit `2` |
| other events | stderr log and non-zero exit |

For `preToolUse`, non-blocking configured failures are logged and swallowed because the official docs make command `preToolUse` fail-closed.

## Reusable Project Scripts

Prefer repo-owned scripts for behavior that may need to move between Copilot, Devin, Codex, OpenCode, Git hooks, GitHub Actions, or a local shell.

Plan shape:

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
      "cwd": ".",
      "notes": "Script is repo-owned and can also be called by CI or other agent adapters."
    }
  ],
  "commands": []
}
```

Resolve `path` relative to the target project root. Keep the shared script path-agnostic by discovering the repo root at runtime and by accepting a harness/mode argument when output protocols differ.

## Plan File Shape

Use a small JSON file like `templates/hook-plan.example.json`:

```json
{
  "hooks_target": ".github/hooks/copilot-hooks.json",
  "managed_root": ".github/copilot/hooks/generated",
  "mode": "additive",
  "enabled_events": [
    {
      "name": "preToolUse",
      "matcher": "bash",
      "timeoutSec": 15,
      "block_on_failure": true,
      "scripts": [],
      "commands": [],
      "notes": "Use this for hard policy and safety gates."
    }
  ]
}
```

The scaffold script treats every event not listed in `enabled_events` as disabled but still creates its stub script.

## User-Level CLI Hooks

Copilot CLI also loads user-level hooks from `~/.copilot/hooks/*.json`, or `$COPILOT_HOME/hooks/*.json` when `COPILOT_HOME` is set.

Use user-level hooks for personal notifications or local-only policy. Do not put project policy there, because cloud agent will not load it and teammates will not share it by default.

## Hooks Target Rules

- Prefer `.github/hooks/copilot-hooks.json` for generated repository hooks.
- Do not place generated hooks under `.github/copilot/settings*.json` unless the user explicitly asks for CLI-only inline hooks.
- Do not place generated hooks under `.claude/settings*.json`.
- If an existing `.github/hooks/copilot-hooks.json` already owns project hooks, update that file additively unless there is a strong reason to overhaul the managed layer.

## See Also

- `references/hook-events.md`
- `references/merge-strategy.md`
- `references/reusable-scripts.md`
