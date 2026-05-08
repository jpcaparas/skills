# Feature Flag

Codex hooks use the canonical `hooks` feature flag. The old `codex_hooks` key is a legacy alias accepted by current source for backward compatibility.

Official sources:

- `https://developers.openai.com/codex/hooks`
- `https://developers.openai.com/codex/config-basic`
- `https://developers.openai.com/codex/config-reference`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/features/src/lib.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/features/src/legacy.rs`

As of the 2026-05-08 verification pass, `codex features list` reports `hooks stable true`, and source maps legacy `codex_hooks` to the same feature. Write canonical `[features].hooks = true` when editing config.

## What To Inspect First

Use the helper script:

```bash
python3 scripts/check_hooks_feature.py --project /absolute/path/to/project --json
```

That checks:

- the effective `hooks` state in the target project
- the user config path and explicit canonical or legacy value, if any
- the project config path and explicit canonical or legacy value, if any
- the current Codex CLI version, if available

You can also inspect the effective state directly:

```bash
codex -C /absolute/path/to/project features list | rg '^hooks\s'
```

## Choosing Scope

Use `--scope project` when:

- the hook scaffold should be shareable in the repo
- committing `.codex/config.toml` is acceptable
- teammates should get the feature enabled when the project config is active

Use `--scope user` when:

- the setup is personal or machine-local
- the repo should not commit `.codex/config.toml`
- you want the feature available across many projects

## Enabling The Feature

Enable project scope:

```bash
python3 scripts/check_hooks_feature.py --project /absolute/path/to/project --enable --scope project
```

Enable user scope:

```bash
python3 scripts/check_hooks_feature.py --project /absolute/path/to/project --enable --scope user
```

Re-run the inspection after enabling. The helper writes `[features].hooks = true`; if it finds an existing `codex_hooks` line in the `[features]` table, it migrates that line to `hooks`.

## Trust Rule

From the official config basics page:

- user defaults live in `~/.codex/config.toml`
- project overrides live in `.codex/config.toml`
- Codex loads project config files only when you trust the project

That means a repo-local `.codex/config.toml` can contain `hooks = true`, but the effective feature can still look off until the project config layer is active.

## Precedence Recap

Current precedence from highest to lowest:

1. CLI flags and `--config`
2. profiles
3. trusted project config files
4. user config
5. system config
6. built-in defaults

Project scope is not "stronger" than user scope if the project layer is inactive.
