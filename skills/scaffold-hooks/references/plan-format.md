# Universal Plan Format

Start from `templates/hook-plan.example.json`.

## Top-Level Fields

| Field | Meaning |
| --- | --- |
| `mode` | `additive` or `overhaul`; defaults to `additive` |
| `hooks_root` | Shared root for shell event scripts and adapters; defaults to `hooks` |
| `cleanup_legacy` | Remove old managed generated folders after config migration; defaults to `true` |
| `harnesses` | Harnesses to scaffold: `claude`, `codex`, `devin`, `opencode` |
| `plans` | Per-harness plan objects passed to the dedicated scaffolders |

## Per-Harness Plans

The nested `plans.claude`, `plans.codex`, `plans.devin`, and `plans.opencode` objects intentionally mirror the dedicated skill plan files. The universal script injects the shared hook root and mode; keep harness-specific settings inside the nested plan.

## Scripts and Commands

Use `scripts` for repo-owned reusable files:

```json
{
  "name": "Stop",
  "timeout": 300,
  "scripts": [
    {
      "label": "shared stop checks",
      "path": "scripts/agent-stop-checks.sh",
      "args": ["codex"],
      "cwd": "."
    }
  ],
  "commands": []
}
```

Use `commands` only for existing task-runner commands that are already safe to run in the target project:

```json
{
  "label": "typecheck",
  "command": "npm run typecheck",
  "cwd": "."
}
```

Keep package-manager assumptions out of the universal template. Put them in project-specific plans.

## Missing Nested Plan

If a nested plan is missing, `scripts/scaffold_all_hooks.sh` falls back in this order:

1. Existing legacy plan in the target project, if present
2. The dedicated harness skill template

This makes migrations practical without copying old generated files.

