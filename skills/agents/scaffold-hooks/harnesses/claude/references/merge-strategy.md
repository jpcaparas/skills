# Merge Strategy

This skill treats Claude adapters and `hooks/.state/claude` as managed. The shared `hooks/<event>/script.sh` files and any non-Claude adapters are user-owned unless the current Claude scaffold created them and they are missing.

## Additive Mode

Use `additive` when the project already has useful hook scripts or settings that should stay in place.

Behavior:

- Create missing `hooks/<event>/script.sh` files and Claude adapter/config files.
- Refresh `hooks/.state/claude/manifest.json`, `hooks/.state/claude/settings.json`, and `hooks/README.md`.
- Remove only Claude managed handlers whose commands point at `hooks/<event>/claude.sh`, then add the new Claude handlers back.
- Leave unrelated custom hooks and non-Claude adapters alone.
- Leave existing shared event script bodies alone if they already exist.

## Overhaul Mode

Use `overhaul` when the Claude adapter layer is stale, inconsistent, or based on an outdated event set.

Behavior:

- Replace `hooks/.state/claude` and `hooks/<event>/claude.{sh,json}`.
- Re-render missing or reset shared `script.sh` files only where the scaffold owns the event script.
- Rebuild `hooks/README.md`.
- Do not move or delete the whole `hooks/` tree.

## Docs Drift Rule

Before every real scaffold or refresh, verify the live official hook docs, compare them with `assets/hook-events.json`, update manifest inputs if needed, then re-run the scaffold.
