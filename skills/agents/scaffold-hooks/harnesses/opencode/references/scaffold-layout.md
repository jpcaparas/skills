# Scaffold Layout

## Target Layout

Project-local default:

```text
opencode.json
.opencode/
└── hook/
    ├── hooks.md
    ├── README.md
    └── .managed/
        ├── manifest.json
        └── plan.snapshot.json
```

Global scope uses:

```text
~/.config/opencode/opencode.json
~/.config/opencode/hook/hooks.md
~/.config/opencode/hook/.managed/
```

The default Froggy scaffold must not create:

- `.opencode/plugins/*.ts`
- `.opencode/package.json`
- `.opencode/package-lock.json`
- `.opencode/node_modules`
- `hooks/opencode-session-created/`
- `hooks/opencode-session-idle/`

Those are old local-plugin scaffold artifacts.

## Plan Fields

Use `templates/hook-plan.example.json`.

- `scope`: `project` or `global`
- `mode`: `additive` or `overhaul`
- `plugin_name`: `opencode-froggy`
- `hooks_root`: used only for old-adapter cleanup coordination
- `config_target`: OpenCode config file
- `hook_config_target`: Froggy hook file
- `managed_state_dir`: manifest and plan snapshot directory
- `hooks`: Froggy hook entries

Each hook entry:

- `event`
- optional `conditions`
- `actions`
- optional `notes`

Keep project-specific decisions in the plan and repo-owned scripts, not in the scaffolder.
