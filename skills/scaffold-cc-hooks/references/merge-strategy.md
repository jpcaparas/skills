# Merge Strategy

This skill treats the generated hook layer as managed and everything else as user-owned.

## Additive Mode

Use `additive` when the project already has useful hook scripts or settings that should stay in place.

Behavior:

- Create missing managed event stubs.
- Refresh `manifest.json`, `settings.generated.json`, and `.claude/hooks/README.md`.
- Remove only previously managed handlers from the chosen settings file, then add the new managed handlers back.
- Leave unrelated custom hooks alone.
- Leave existing managed event script bodies alone if they already exist.

Use additive mode when:

- the project already has a stable managed generated tree
- the user mainly wants new event coverage
- the user wants the current custom logic preserved

## Overhaul Mode

Use `overhaul` when the managed generated layer is stale, inconsistent, or based on an outdated event set.

Behavior:

- Re-render every managed event stub from the current template.
- Rebuild `manifest.json`, `settings.generated.json`, and `.claude/hooks/README.md`.
- Remove only previously managed handlers from the chosen settings file, then add the new managed handlers back.
- Keep unrelated non-managed hooks unless the user explicitly asks you to remove them.

Use overhaul mode when:

- the official event set changed
- the generated layer drifted away from the current structure
- the repo wants a clean reset of the managed hook scaffold

## Docs Drift Rule

Before every real scaffold or refresh:

1. Verify the live official hook docs.
2. Compare them with `assets/hook-events.json`.
3. If the event set or support matrix changed, update the manifest inputs first.
4. Then re-run the scaffold in the target project.

Do not assume the baked-in event list is still current.

