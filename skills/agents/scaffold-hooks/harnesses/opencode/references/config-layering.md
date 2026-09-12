# Config Layering

Verified on 2026-06-21 against the OpenCode plugin/config docs and `opencode-froggy@0.12.0`.

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
