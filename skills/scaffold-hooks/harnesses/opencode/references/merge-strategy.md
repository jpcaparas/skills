# Merge Strategy

## Additive Mode

Additive mode:

- adds `opencode-froggy` to the `plugin` array in `opencode.json`
- renders or refreshes the managed block inside `.opencode/hook/hooks.md`
- preserves appendable custom hooks in the same `hooks:` list
- preserves unrelated config keys and plugin entries
- preserves unmanaged `.opencode/plugins/*.ts`
- removes old scaffold-owned plugin artifacts when `.opencode/plugins/.managed/manifest.json` proves ownership

## Overhaul Mode

Overhaul mode still preserves unrecognized custom `hooks.md` files. It replaces the managed Froggy block, or replaces the whole file only when the file is already scaffold-managed.

Use overhaul when:

- the managed Froggy plan changed substantially
- old managed content is misleading
- the target should match the current plan exactly

## Legacy Cleanup

When the old local-plugin scaffold is detected:

- remove files listed in `.opencode/plugins/.managed/manifest.json`
- remove `.opencode/plugins/.managed/`
- remove generated `.opencode/plugins/README.md`
- remove generated `hooks/opencode-session-created` and `hooks/opencode-session-idle` adapters when they still match the old generated shape
- remove `.opencode/package.json`, lockfiles, and `node_modules` only when package metadata contains only the old `@opencode-ai/plugin` dependency

Do not remove unmanaged local plugins or user-owned Froggy hooks.
