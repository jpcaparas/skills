# Universal Plan Format

Start from `templates/hook-plan.example.json`.

## Top-Level Fields

| Field | Meaning |
| --- | --- |
| `mode` | `additive` or `overhaul`; defaults to `additive` |
| `hooks_root` | Shared root for shell event scripts and adapters; defaults to `hooks` |
| `cleanup_legacy` | Remove old managed generated folders after config migration; defaults to `true` |
| `harnesses` | Harnesses to scaffold: `claude`, `codex`, `copilot`, `devin`, `opencode` |
| `plans` | Per-harness plan objects passed to the dedicated scaffolders |
| `code_change_extensions` | Optional top-level extension override for shell Stop code-change gates; defaults to project detection |

## Harness Selection

When `scripts/scaffold_all_hooks.sh` runs without `--harnesses`, selection is conservative:

1. A custom universal plan's `harnesses` list wins when present.
2. With the default plan, existing hook surfaces or managed scaffold state in the target repo define the refresh set.
3. The default all-supported set is used only when no supported hook surface is detected.

Use `--harnesses` when intentionally adding harnesses. A bare re-run on a repo with existing hooks must not expand to new harnesses.

## Managed Manifest Provenance

Every universal run writes `hooks/.state/scaffold-hooks/manifest.json`. It records:

- `scaffold_hooks.skill_version`
- `scaffold_hooks.source`
- `scaffold_hooks.generator.sha256`
- `scaffold_hooks.harness_manifest_sha256`
- `scaffold_hooks.plan_sha256`
- selected `mode`, `hooks_root`, `harnesses`, detected harnesses, harness selection source, and `cleanup_legacy`

Harnesses can add more granular provenance. OpenCode records `managed_file_hashes` and `preserved_file_hashes` so additive re-runs can apply template improvements to unchanged managed plugin files while preserving local edits.

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

## Stop Code-Change Gates

Claude, Codex, and Devin Stop adapters default to `run_on_code_changes: true`. During scaffolding, the generator scans the target project and stores detected source/config extensions in each Stop adapter config:

```json
{
  "name": "Stop",
  "timeout": 300,
  "run_on_code_changes": true,
  "code_change_extensions": ["php", "ts", "tsx"],
  "scripts": [
    {
      "label": "shared stop checks",
      "path": "scripts/agent-stop-checks.sh",
      "args": ["claude"],
      "cwd": "."
    }
  ]
}
```

Use `run_on_code_changes: false` when a Stop hook must run on every turn. Use `code_change_extensions` when the detector misses project-specific source files or includes file types that should not trigger expensive checks.

## Missing Nested Plan

If a nested plan is missing, `scripts/scaffold_all_hooks.sh` falls back in this order:

1. Existing legacy plan in the target project, if present
2. The dedicated harness skill template

This makes migrations practical without copying old generated files.
