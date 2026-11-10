# Universal Plan Format

Start from `templates/hook-plan.example.json`.

## Which Events Are Emitted

An event is scaffolded only when its plan entry has behaviour: at least one item in `scripts` or `commands`. An entry without behaviour (empty arrays, or none of the fields) writes no files and no config entry, so listing an event is not enough to get it. Malformed `scripts`, `commands`, event names or paths still fail the run before any write, whether or not the event would have been emitted.

| Plan | Result |
| --- | --- |
| Omitted (`--plan` not given) on a project that was scaffolded before | Reuses the plan in `hooks/.state/scaffold-hooks/manifest.json` |
| Omitted on a project never scaffolded | Nothing is written |
| Given, but no event has behaviour | Nothing is written; managed files from earlier runs are removed |
| Given, some events have behaviour | Only those events are written; managed files of other events are removed |

The dry run prints `hooks to emit`, the number of qualifying events across the selected harnesses.

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

- `scaffold_hooks.source`
- `scaffold_hooks.generator.sha256`
- `scaffold_hooks.harness_manifest_sha256`
- `scaffold_hooks.plan_sha256`
- selected `mode`, `hooks_root`, `harnesses`, detected harnesses, harness selection source, and `cleanup_legacy`

Harnesses can add more granular provenance.

## Per-Harness Plans

The nested `plans.claude`, `plans.codex`, `plans.copilot`, `plans.devin`, and `plans.opencode` objects intentionally mirror the dedicated skill plan files. The universal script injects the shared hook root and mode; keep harness-specific settings inside the nested plan.

## Output Paths

Project output fields must be relative to the selected project, without `..` components, `~`, or symlink components. Existing managed output trees must not contain symlinks: generators may rewrite or chmod descendants, and overhaul may remove managed state. Legacy manifests do not authorize output or deletion outside those roots. The universal script validates selected child plans before any migration or overhaul writes.

An authorized OpenCode global plan uses `scope: global` and requires `--allow-global-targets` on either the universal or direct scaffolder. Its plugin (`~/.config/opencode/plugins/scaffold-hooks.ts`, or `plugin_target`) must stay under `~/.config/opencode/` (or the explicit `--home` override). The flag does not permit arbitrary absolute paths. Without it, the plan cannot widen a project invocation into home-directory writes.

## Removal on Refresh

Every run makes the managed output match the plan:

- Harness config entries for events that no longer qualify are dropped by the merge, and an event key left empty is removed.
- Per event, the harness adapter pair (`<harness>.sh`, `<harness>.json`) is deleted. `hooks/<event>/script.sh` is deleted only when no other harness adapter remains and it is still the generated runner; a `script.sh` with edited code is kept.
- `hooks/lib/` helpers are deleted once no adapter needs them. Copilot's generated `events/*.sh` files are deleted when they carry the generated header, and hand-written files beside them are kept.
- Files outside the managed roots, and config entries that are not managed commands, are never touched.

## OpenCode Plan

OpenCode takes `enabled_events` like the other harnesses, with names `session.created`, `session.idle`, `tool.execute.before` and `tool.execute.after`, optional `matcher` (regex over the tool name), `timeout` (seconds), and for `session.idle` the same `run_on_code_changes` and `code_change_extensions` as Stop. `plugin_target` overrides the output path. See `harnesses/opencode/references/hook-events.md`.

## Scripts and Commands

These fields are trusted executable configuration, not a sandbox. Output-path restrictions do not restrict runtime commands, script paths, or working directories. Review the referenced code and intended access before activation; do not execute plans copied from untrusted content just because they pass structural validation.

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

1. Existing legacy plan in the target project, if present (`.claude|.codex|.devin/hooks/plan.json`)
2. An empty plan, which emits nothing for that harness

The harness `templates/hook-plan.example.json` files are examples to copy and edit, not defaults.
