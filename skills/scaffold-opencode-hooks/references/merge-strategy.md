# Merge Strategy

This skill treats the generated OpenCode plugin layer as managed and everything else as user-owned.

## Additive Mode

Use `additive` when the project already has useful OpenCode plugins or config that should stay in place.

Additive mode:

- creates missing managed plugin files
- refreshes `manifest.json`, `plan.snapshot.json`, the hook-surface stubs, and `.opencode/plugins/README.md`
- merges npm plugin entries into config without deleting unrelated entries
- merges config-dir dependencies without deleting unrelated dependencies
- leaves existing managed plugin file bodies alone if they already exist
- leaves unrelated user plugins alone

Choose additive when:

- the repo already has custom plugins worth preserving
- the user mainly wants a managed baseline plus missing patterns
- the current managed layer is mostly correct and only needs extension

## Overhaul Mode

Use `overhaul` when the managed layer is stale, misleading, or based on an outdated surface set.

Overhaul mode:

- backs up the old managed state directory before replacing it
- removes previously managed live plugin files recorded in the old manifest
- re-renders every managed live plugin file from the current template
- rebuilds `manifest.json`, `plan.snapshot.json`, the surface stubs, and `.opencode/plugins/README.md`
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

