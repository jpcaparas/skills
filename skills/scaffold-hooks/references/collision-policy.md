# Collision Policy

The universal scaffold is safe only if old managed hook commands are removed before new shared adapters are added.

## Managed Config Entries

The script strips command hooks that reference these legacy roots:

- `.claude/hooks/generated`
- `.codex/hooks/generated`
- `.devin/hooks/generated`

It does not strip prompt hooks, HTTP hooks, MCP hooks, agent hooks, or custom command hooks outside those roots.

## Shared Scripts

`hooks/<event>/script.sh` is user-editable shared behavior. It is never deleted by universal cleanup and is not rewritten by shell harnesses during universal runs.

Harness adapters are disposable:

- `hooks/<event>/claude.sh`
- `hooks/<event>/claude.json`
- `hooks/<event>/codex.sh`
- `hooks/<event>/codex.json`
- `hooks/<event>/devin.sh`
- `hooks/<event>/devin.json`

## Legacy Folder Cleanup

The script removes old generated folders only when they contain `manifest.json`. That guards against deleting user-owned files that happen to live under a similarly named path.

## OpenCode

OpenCode plugin files auto-load from `.opencode/plugins/`. The universal skill does not delete unmanaged plugin files because it cannot prove their intent. If an existing custom plugin duplicates the new managed lifecycle plugin, handle it explicitly in the project plan or delete it after reviewing the code.

## Final Verification

After scaffolding, the script scans final harness configs and fails if any selected shell harness still references a legacy generated root.

