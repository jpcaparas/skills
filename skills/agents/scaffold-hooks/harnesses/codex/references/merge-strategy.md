# Merge Strategy

This skill treats Codex adapters and `hooks/.state/codex` as managed. The shared `hooks/<event>/script.sh` files and any non-Codex adapters are user-owned unless the current Codex scaffold created them and they are missing.

## Additive Mode

Use `additive` when the project already has useful hook handlers or settings that should stay in place.

Behavior:

- Create missing `hooks/<event>/script.sh` files and Codex adapter/config files.
- Refresh `hooks/.state/codex/manifest.json`, `hooks/.state/codex/hooks.json`, and `hooks/README.md`.
- Remove only Codex managed handlers whose commands point at `hooks/<event>/codex.sh`, then add the new Codex handlers back.
- Leave unrelated custom hooks and non-Codex adapters alone.
- Leave existing shared event script bodies alone if they already exist.

## Overhaul Mode

Use `overhaul` when the Codex adapter layer is stale, inconsistent, or based on an outdated event set.

Behavior:

- Replace `hooks/.state/codex` and `hooks/<event>/codex.{sh,json}`.
- Re-render missing or reset shared `script.sh` files only where the scaffold owns the event script.
- Rebuild `hooks/README.md`.
- Do not move or delete the whole `hooks/` tree.

## Cross-File Layering Rule

Codex loads `hooks.json` next to every active config layer. Project-local hooks do not replace user-global hooks, and the managed merge only controls one `hooks.json` file at a time.

## Docs Drift Rule

Before every real scaffold, verify the live official hook docs, compare them with `assets/hook-events.json`, re-check schemas and runtime source for parser changes, and update manifest inputs first if anything changed.
