---
name: better-chezmoi
description: "Use for chezmoi setup and migration, daily dotfile sync, templates, secrets, run_ scripts, drift and conflict recovery, or official chezmoi docs lookup. Not for dotfiles without chezmoi."
---

# Better chezmoi

Reference evidence: official chezmoi docs and release v2.74.0 ([releases](https://github.com/twpayne/chezmoi/releases), published 2026-11-01), checked 2026-11-10; the bundled docs snapshot was refreshed the same day. Command surface exercised on chezmoi v2.74.0 (Linux, 2026-11-10) and earlier on v2.70.2 (macOS). The installed binary owns executable syntax: run `chezmoi --version` and `chezmoi <command> --help` before using a flag that may be newer than the binary.

## Authority

A request to add, edit, apply, update, merge or remove a named target authorizes that scoped effect only. It does not authorize applying every target, enabling `git.autoPush`, pushing, rewriting remote history, exposing secrets, or destroying source and target state. Scope commands to the named targets, and preview before any target write unless the user asked for immediate application.

On Windows, give PowerShell-native forms; do not offer POSIX arrays, `$(...)` or `mktemp`.

## Default loop

Capture the version and `chezmoi source-path`, then edit source state (`chezmoi edit`), preview, apply, verify:

```sh
chezmoi diff --exclude=scripts --no-pager [target...]
chezmoi apply --dry-run --verbose --exclude=scripts [target...]
chezmoi apply --exclude=scripts [target...]
chezmoi verify --exclude=scripts [target...]
```

`--exclude=scripts` keeps scripts out of the preview; account for them separately. Report the version, scope, commands run, and any remaining drift.

## What the previews do not guarantee

- `--dry-run` only guarantees the destination is untouched. `init` can still create source Git state, hooks run even in dry-run, and templates or externals can reach the network or a password manager.
- `edit --apply` and `edit --watch` apply on every save; use them only when the user wants that.
- `diff` exits 0 even when it shows differences, and its `--output` did not redirect on v2.70.2 or v2.74.0. `verify` exits 0 on match and 1 on mismatch; use it for drift checks. `status` has two columns: actual vs last-written state, and actual vs desired state (what `apply` would do); `A D M R` are add, delete, modify, run.
- `--error-on-conflict` (fail closed instead of prompting) and `init --revision/--tag` arrived in v2.71.0, and docs use `-w` for `--working-tree` where the v2.70.2 and v2.74.0 binaries show `-W`. On an older binary, stop or upgrade; never substitute `--force` for conflict handling.

## Gotchas

- `update` pulls and applies; it is not a preview. For review first: `chezmoi update --apply=false`, or `chezmoi git pull -- --autostash --rebase` then `diff`. Either changes the local source repository and uses the network.
- `re-add` does not update templated sources. For a template, edit it or use `merge`.
- Source wins: scoped `apply`. Destination wins (non-template): `re-add`. Both have changes: `merge TARGET` or `merge-all`.
- `--source-path` reinterprets target arguments as source paths, and relative ones resolve from the current directory; pass absolute paths.
- `managed --format=json` can still emit newline-separated paths; v2.70.2 and v2.74.0 needed `--path-style=all` for the keyed structure.
- A template that renders empty removes its target unless the source has the `empty_` attribute.
- `chezmoi cd` opens a child shell. Use `cd "$(chezmoi source-path)"` to move the caller.
- `init` with `--apply` is a bootstrap. One-shot mode removes chezmoi's own source and config afterward; say so before using it.

## Templates and machine differences

Source files ending `.tmpl` (or under `.chezmoitemplates/`) are templates. Data merges in order: built-in `.chezmoi`, `.chezmoidata` files, then config `data`, later overriding earlier. Keep portable defaults in source data and machine-specific values (email, role) in the local config. Prefer `.chezmoi.os`/`.chezmoi.arch` or named config data over hostname tests. Select targets per machine with a templated `.chezmoiignore`, checked with `chezmoi ignored` and `chezmoi diff`.

Test with `chezmoi data --format=yaml`, `chezmoi execute-template '{{ .chezmoi.os }}'`, then `chezmoi cat TARGET`; preview each machine class affected. `add --autotemplate` substitutes greedily, so treat it as a draft.

## Secrets

Plaintext secrets never go into source history or output. Use `chezmoi add --secrets=error TARGET` when capturing files, then route the value to a password-manager template function, encrypted source (`add --encrypt`, only after recipient keys and recovery are verified), or untracked local config. `chezmoi edit` decrypts transparently; keep its temporary plaintext out of logs.

## Scripts and locks

- `run_` runs every apply; `run_onchange_` when rendered content changes; `run_once_` once per unique content; `before_`/`after_` set the phase, alphabetical within it. Keep scripts idempotent. A template script's `#!` must be at byte zero. A failed `run_once_`/`run_onchange_` can run again.
- Never call chezmoi from a `run_` script: persistent-state locks make the nested call time out.
- Write-lock commands: add, apply, edit, forget, import, init, state, unmanage, update. diff, status and verify take read locks. On a lock timeout, find the other chezmoi process or nested call and wait for or stop that owner. Delete the persistent-state database only with official guidance and a backup.

## Removal

`forget`/`unmanage` stop managing a target and leave it on disk. `destroy` deletes source and target permanently; `purge` removes chezmoi config, state and source. Never infer `destroy` from "stop managing"; use it only with exact targets, an independent backup and explicit confirmation. For `.chezmoiremove` patterns, dry-run verbosely and inspect each match.

## Official docs

`references/official-docs/` is a searchable snapshot of selected chezmoi.io pages (index in `manifest.json`):

```sh
python3 scripts/official_docs.py search "persistent state lock" --limit 20
python3 scripts/official_docs.py refresh
```

`refresh` fetches and compares without replacing the snapshot and reports added, changed, removed and unchanged pages. `refresh --write` replaces the snapshot with a validated copy; run it only when the user has authorized updating the corpus, then `python3 scripts/official_docs.py check`. For an ad hoc refresh elsewhere, use `--output` with a scratch directory and search it with `--docs`. A network failure is not evidence the snapshot is current. The `DOCUMENT_SOURCES` tuple in the script owns the page list; add a page only when a real task needs it.
