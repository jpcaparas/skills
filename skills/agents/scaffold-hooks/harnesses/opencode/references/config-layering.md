# Config Layering

> **Drift, 2026-11-10 (unresolved).** `opencode-froggy` 1.7.0+ no longer loads `.opencode/hook/hooks.md`, and OpenCode marks the `plugin` config key deprecated in favour of `plugins`. This scaffold still targets the 0.12.0-era Froggy behaviour below. Evidence and open questions: `assets/hook-events.json` under `drift_2026_11_10`. Until the owner decides (pin a hook-capable Froggy, or move to a native OpenCode plugin), do not tell a user the generated hooks will run on a current Froggy; check with `opencode plugin list` and a live session.

Verified on 2026-06-21 against the OpenCode plugin/config docs and `opencode-froggy@0.12.0`.

This is a historical verification baseline, not a required installation version. Resolve uncertain or changing behavior against official OpenCode docs and trusted Froggy source for the installed version; preserve deterministic pins unless an authorized, verified update needs them changed.

## OpenCode Plugin Loading

This scaffold enables Froggy by merging `opencode-froggy` into the OpenCode config `plugin` array. Project scope defaults to `opencode.json`; global scope defaults to `~/.config/opencode/opencode.json`.

The merge is additive:

- keep unrelated config keys
- keep unrelated plugin entries
- add `opencode-froggy` only if missing
- normalize JSON/JSONC output to JSON

## Froggy Hook Loading

Froggy reads hook files from:

- global: `~/.config/opencode/hook/hooks.md`
- project: `.opencode/hook/hooks.md`
- Windows global fallback: `%APPDATA%/opencode/hook/hooks.md` when that file exists and the `~/.config` hook file does not

Froggy merges global hooks first, then project hooks. A project scaffold cannot disable global Froggy hooks.

## Scope Guidance

Use project scope when:

- the hook behavior should travel with the repo
- hooks call repo-owned scripts
- teammates should share the same baseline

Use global scope when:

- the hook behavior is personal
- the repo should not contain OpenCode config
- the same hooks should apply across many repos

## Legacy Plugin Layer

The previous scaffold generated local TypeScript plugins under `.opencode/plugins/`. That path can still contain user-owned OpenCode plugins, but this Froggy-backed scaffold does not create files there. Remove only files proven managed by `.opencode/plugins/.managed/manifest.json`.
