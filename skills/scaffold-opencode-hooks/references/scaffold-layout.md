# Scaffold Layout

## Minimal Managed Target Layout

Project-local default for lifecycle/action work:

```text
.opencode/
└── plugins/
    ├── README.md
    └── opencode_hook_project_session_lifecycle.ts
```

The minimal scaffold intentionally skips `opencode.json`, `.opencode/package.json`, `node_modules`, lockfiles, and broad hook-surface stubs unless the plan actually needs them.

## Broad Managed Target Layout

Use this only when the user asks for a broad surface catalog:

```text
opencode.json                     # Optional, only when npm plugin entries are part of the plan
.opencode/
├── package.json                  # Created only when generated plugins import external packages
└── plugins/
    ├── README.md                 # Generated plugin and hook-surface map
    ├── opencode_hook_guard.ts    # Managed live plugin module
    ├── opencode_hook_post_turn.ts
    ├── opencode_hook_shell_env.ts
    └── .managed/
        ├── manifest.json         # Snapshot of the scaffold inputs used
        ├── plan.snapshot.json    # Normalized plan used for generation
        └── surfaces/
            ├── command.executed.ts.txt
            ├── file.edited.ts.txt
            ├── ...
            └── experimental.session.compacting.ts.txt
```

Global scope uses the same shape under `~/.config/opencode/`.

## Why This Layout

- live plugin files stay in the documented plugin load path
- dormant surface stubs stay out of the runtime load path when broad mode is requested
- the managed state directory is easy to replace or inspect
- config and dependency merges stay separate from plugin-file generation
- the README gives the target project a stable event and plugin map
- the active load path contains TypeScript plugin modules only; this scaffold rewrites any `.js` filename in a plan to `.ts`

## Plan File Shape

Use `templates/hook-plan.example.json` as the starting point.

Top-level fields:

- `scope`
- `deployment`
- `mode`
- `module_format` (`ts` only)
- `surface_catalog` (`false` for minimal, `true` for broad)
- `plugin_root`
- `managed_state_dir`
- `config_target`
- `package_target`
- `package_dependencies`
- `npm_plugins`
- `enabled_plugins`

Each enabled plugin entry carries:

- `name`
- `pattern` (`lifecycle-action` for the minimal reusable pattern; omit for broad surface handlers)
- `filename`
- `surfaces`
- optional `context_script`, `action_script`, `action_label`, and `service`
- `notes`

For lifecycle/action plugins, `context_script` and `action_script` are resolved against OpenCode's active project/worktree/directory context. Do not assume `.opencode/plugins/../..` is the repo root, because global plugins and custom config directories break that assumption.

Keep project-specific judgment in the plan. The scaffold should remain deterministic.
