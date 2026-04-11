# Merge Strategy

This skill treats the generated hook layer as managed and everything else as user-owned.

## Additive Mode

Use `additive` when the project already has useful hook handlers or settings that should stay in place.

Additive mode:

- creates missing managed event stubs
- refreshes `manifest.json`, `hooks.generated.json`, and `.codex/hooks/README.md`
- removes only previously managed handlers from `.codex/hooks.json`, then adds the new managed handlers back
- leaves unrelated custom handlers alone
- leaves existing managed event script bodies alone if they already exist

Choose additive when:

- the repo already has custom hooks worth preserving
- the user mainly wants missing event coverage or a managed README
- the managed root is mostly correct and only needs extension

## Overhaul Mode

Use `overhaul` when the managed layer is stale, inconsistent, or based on an outdated event set.

Overhaul mode:

- backs up the old managed root before replacing it
- re-renders every managed event stub from the current template
- rebuilds `manifest.json`, `hooks.generated.json`, and `.codex/hooks/README.md`
- removes only previously managed handlers from `.codex/hooks.json`, then adds the new managed handlers back
- keeps unrelated non-managed hooks unless the user explicitly asks to remove them

Choose overhaul when:

- the official event set changed
- the runtime semantics changed enough that old stubs are misleading
- the repo wants a clean reset of the managed hook scaffold

## Cross-File Layering Rule

Codex loads `hooks.json` next to every active config layer. That means:

- project-local hooks do not replace user-global hooks
- higher-precedence config layers do not wipe lower-precedence hook files
- the managed merge only controls one `hooks.json` file at a time

Do not pretend a project scaffold owns `~/.codex/hooks.json` unless the plan explicitly targets user scope.

## Docs Drift Rule

Before every real scaffold:

1. Verify the live official hook docs.
2. Compare them with `assets/hook-events.json`.
3. Re-check the generated schemas and runtime source for parser changes.
4. If the event set or support matrix changed, update the manifest inputs first.

Do not trust early blog posts or stale local assumptions over the official docs and schemas.
