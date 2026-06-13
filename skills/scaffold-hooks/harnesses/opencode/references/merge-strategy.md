# Merge Strategy

This skill treats the generated OpenCode plugin layer as managed and everything else as user-owned.

## Additive Mode

Use `additive` when the project already has useful OpenCode plugins or config that should stay in place.

Additive mode:

- creates missing managed plugin files
- refreshes managed plugin files whose current hash still matches the prior manifest hash
- preserves existing managed plugin files whose current hash differs from the prior manifest hash
- refreshes `manifest.json`, `plan.snapshot.json`, optional hook-surface stubs, and `.opencode/plugins/README.md`
- merges npm plugin entries into config without deleting unrelated entries
- merges config-dir dependencies without deleting unrelated dependencies when dependencies are needed
- leaves unrelated user plugins alone

Choose additive when:

- the repo already has custom plugins worth preserving
- the user mainly wants a managed baseline plus missing patterns
- the current managed layer is mostly correct and only needs extension

For legacy manifests created before `managed_file_hashes`, additive mode can still refresh a file when both are true:

- the previous manifest lists it in `managed_files`
- the file still contains the scaffold-managed header

The old file is copied under `.opencode/plugins/.managed/backups/` before refresh.

## Overhaul Mode

Use `overhaul` when the managed layer is stale, misleading, or based on an outdated surface set.

Overhaul mode:

- backs up the old managed state directory before replacing it
- removes previously managed live plugin files recorded in the old manifest
- re-renders every managed live plugin file from the current template
- rebuilds `manifest.json`, `plan.snapshot.json`, optional surface stubs, and `.opencode/plugins/README.md`
- keeps unrelated non-managed plugins unless the user explicitly asks to remove them
- preserves unrelated config keys, plugin-array entries, and package dependencies

Choose overhaul when:

- the official surface set changed
- the runtime semantics changed enough that old stubs are misleading
- the managed plugin filenames or module format need a clean reset

## Cross-Layer Rule

OpenCode loads plugins from all configured sources in sequence. That means:

- project-local plugins do not replace global plugins
- npm plugin entries do not replace local plugin files
- a project-local scaffold does not own `~/.config/opencode/plugins/`

Do not pretend one managed scaffold owns every OpenCode source layer unless the plan explicitly targets that scope.

## Provenance Fields

The managed manifest records:

- `scaffold_hooks.skill_version`
- `scaffold_hooks.source`
- `scaffold_hooks.generator.sha256`
- `scaffold_hooks.plan_sha256`
- `scaffold_hooks.templates`
- `managed_file_hashes`
- `preserved_file_hashes`

Use these fields to decide whether a re-run can apply template improvements incrementally. If a file is preserved because its hash changed, use `overhaul` only after reviewing the local edits.
