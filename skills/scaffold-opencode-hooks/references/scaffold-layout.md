# Scaffold Layout

## Managed Target Layout

Project-local default:

```text
opencode.json                     # Optional, only when npm plugin entries are part of the plan
.opencode/
├── package.json                  # Created when the scaffold needs stable module semantics or config-dir dependencies
└── plugins/
    ├── README.md                 # Generated plugin and hook-surface map
    ├── opencode_hook_guard.js    # Managed live plugin module
    ├── opencode_hook_post_turn.js
    ├── opencode_hook_shell_env.js
    └── .managed/
        ├── manifest.json         # Snapshot of the scaffold inputs used
        ├── plan.snapshot.json    # Normalized plan used for generation
        └── surfaces/
            ├── command.executed.js.txt
            ├── file.edited.js.txt
            ├── ...
            └── experimental.session.compacting.js.txt
```

Global scope uses the same shape under `~/.config/opencode/`.

## Why This Layout

- live plugin files stay in the documented plugin load path
- dormant surface stubs stay out of the runtime load path
- the managed state directory is easy to replace or inspect
- config and dependency merges stay separate from plugin-file generation
- the README gives the target project a stable event and plugin map

## Plan File Shape

Use `templates/hook-plan.example.json` as the starting point.

Top-level fields:

- `scope`
- `deployment`
- `mode`
- `module_format`
- `plugin_root`
- `managed_state_dir`
- `config_target`
- `package_target`
- `package_dependencies`
- `npm_plugins`
- `enabled_plugins`

Each enabled plugin entry carries:

- `name`
- `filename`
- `surfaces`
- `notes`

Keep project-specific judgment in the plan. The scaffold should remain deterministic.
