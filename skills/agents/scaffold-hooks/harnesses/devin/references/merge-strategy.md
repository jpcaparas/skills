# Merge Strategy

This skill treats Devin adapters and `hooks/.state/devin` as managed. The shared `hooks/<event>/script.sh` files and any non-Devin adapters are user-owned unless the current Devin scaffold created them and they are missing.

## Additive Mode

Use `additive` when the project already has useful hook scripts or hook config that should stay in place.

Behavior:

- Create missing `hooks/<event>/script.sh` files and Devin adapter/config files.
- Refresh `hooks/.state/devin/manifest.json`, `hooks/.state/devin/hooks.v1.json`, and `hooks/README.md`.
- Remove only Devin managed handlers whose commands point at `hooks/<event>/devin.sh`, then add the new Devin handlers back.
- Leave unrelated custom hooks and non-Devin adapters alone.
- Leave existing shared event script bodies alone if they already exist.

## Overhaul Mode

Use `overhaul` when the Devin adapter layer is stale, inconsistent, or based on an outdated event set.

Behavior:

- Replace `hooks/.state/devin` and `hooks/<event>/devin.{sh,json}`.
- Re-render missing or reset shared `script.sh` files only where the scaffold owns the event script.
- Rebuild `hooks/README.md`.
- Do not move or delete the whole `hooks/` tree.

## Docs Drift Rule

Before every real scaffold or refresh, verify the live official hook docs, compare them with `assets/hook-events.json`, update manifest inputs if needed, then re-run the scaffold.
