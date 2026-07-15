---
name: better-chezmoi
description: "Use for safe chezmoi setup and migration, daily dotfile sync, templates, secrets, scripts, drift/recovery, or official-doc research."
---

# Better chezmoi

Use chezmoi through an inspect, preview, apply, and verify loop. Keep source state, target state, local configuration, remote Git, and external effects distinct so a convenient command does not silently widen the user's request.

## Operating contract

- Current reference evidence: official chezmoi documentation and release v2.71.0, checked 2026-07-15.
- Locally exercised command surface: chezmoi v2.70.2 on macOS, including a fully isolated source, destination, config, cache, and persistent-state harness.
- Version rule: run `chezmoi --version` and inspect `chezmoi <command> --help` before using a version-sensitive flag. The installed binary owns executable syntax; the scraped documentation supplies current concepts, examples, and newly released behavior.
- Authority rule: an explicit request to add, edit, apply, update, merge, or remove a named target authorizes that scoped effect. It does not authorize applying every target, enabling auto-push, rewriting remote history, exposing secrets, or destroying source and target state.
- Portability: show PowerShell-native forms for Windows users. Do not present POSIX shell arrays, command substitution, or `mktemp` as portable Windows syntax.

## Route the task

| User goal | Read | Use it to |
|---|---|---|
| Inspect, add, edit, capture, preview, apply, or sync dotfiles | `references/daily-workflows.md` | choose the narrowest daily loop and its verification |
| Initialize a repository, bootstrap a new machine, or separate machine-specific state | `references/setup-and-machines.md` | choose init, source/config placement, and cross-machine boundaries |
| Build or debug templates, data, secrets, encrypted files, or scripts | `references/templates-secrets-and-scripts.md` | test rendering and keep sensitive or effectful data out of source history |
| Diagnose drift, conflicts, locks, merges, or destructive cleanup | `references/recovery-and-safety.md` | identify state ownership and select a reversible recovery route |
| Need exact commands, flags, output, or exit semantics | `references/commands.md` | verify the current command form and effect class |
| Need current official detail or want to refresh/search the bundled corpus | `references/official-documentation.md` | run the deterministic scraper and inspect provenance |

Load only the rows needed for the task. For a simple `status` explanation, do not load setup, templates, or recovery material.

## Classify effects first

| Effect class | Examples | Default handling |
|---|---|---|
| Read/check | `--version`, `help`, `source-path`, `target-path`, `status`, `diff`, `verify`, `doctor --no-network` | run when useful; still account for template evaluation, hooks, and cached externals |
| Source write | `add`, `edit`, `re-add`, `forget`, `init`, Git pull | scope to named targets; preview where supported; verify source diff |
| Target write | `apply`, `edit --apply`, default `update`, `init --apply` | preview first unless the user explicitly requests immediate application |
| Local config/state | `edit-config`, init config templates, script state, purge | inspect paths and recovery before changing them |
| Remote/network | Git fetch/pull, externals, password managers, auto-commit/push | keep reads bounded; require explicit authority for remote writes or secret access |
| Destructive | `destroy`, broad removal rules, `purge` | require exact scope, independent backup, preview where available, and postcondition checks |

`--dry-run` guarantees that chezmoi does not modify the destination directory. It is not a universal no-side-effects mode: init can still create source Git state, hooks run even in dry-run mode, and templates or externals can invoke networked dependencies. Describe the narrower guarantee exactly.

## Core workflow

### 1. Inspect the active context

Run the smallest useful set:

```sh
chezmoi --version
chezmoi source-path
chezmoi target-path
chezmoi status --exclude=scripts
```

Use `chezmoi doctor --no-network` when setup or dependency health is in question. Inspect the relevant command's local help before introducing flags from the bundled docs.

**Complete when:** the installed version, source and destination roots, requested target scope, and likely effect classes are known.

### 2. Inspect the difference

For ordinary target drift or a source edit:

```sh
chezmoi diff --exclude=scripts --no-pager
```

For a target-write preview:

```sh
chezmoi apply --dry-run --verbose --exclude=scripts
```

If a non-interactive preview would stop for a conflict prompt, `--force` may be paired with `--dry-run` only after confirming the local help and dry-run flag. Do not carry `--force` into the real apply.

**Complete when:** the proposed source or target changes are visible, scripts and hooks have been accounted for, and conflicts or unexpected targets are resolved before mutation.

### 3. Perform only the authorized effect

Use the narrowest target list. Prefer one file or subtree over an unscoped apply when the request is narrow. On chezmoi v2.71.0 or newer, use `--error-on-conflict` for non-interactive automation only after the local help confirms it; on older versions, stop rather than replacing conflict handling with `--force`.

Do not enable `git.autoPush`, run a remote push, or commit plaintext secrets unless the user explicitly requests that remote effect and its scope is clear.

**Complete when:** only the named source, target, config, or remote scope changed and the command returned its documented success result.

### 4. Verify the postcondition

Use one or more of:

```sh
chezmoi status --exclude=scripts
chezmoi diff --exclude=scripts --no-pager
chezmoi verify --exclude=scripts
```

Interpret results correctly: `diff` can return 0 while showing differences; `status` communicates drift in two columns; `verify` returns 0 when selected targets match and 1 when they do not.

Report the version checked, source and target scope, commands run, observed effects, and any remaining drift or skipped effect.

**Complete when:** the requested postcondition is independently visible and any nonzero result is classified as expected drift, conflict, operational failure, or unsupported syntax.

## Official documentation corpus

The package includes a searchable snapshot of selected official pages and a standard-library Python tool:

```sh
python3 scripts/official_docs.py search "error-on-conflict"
python3 scripts/official_docs.py list
python3 scripts/official_docs.py refresh
```

`refresh` fetches and compares without replacing the bundled snapshot. Add `--write` only when the user wants to publish the refreshed corpus. Read `references/official-documentation.md` before refreshing or changing the source list; use it to preserve provenance, rollback-safe staged replacement, and offline validation.

## Gotchas

1. `update` is not a preview. It normally pulls the source repository and applies target changes. Use `update --apply=false` or the reviewed pull → diff → apply sequence when the user wants separation.
2. `re-add` does not update templated source files. Use `edit`, `merge`, or an intentional template change instead.
3. Relative arguments under `--source-path` resolve from the current working directory. Use an absolute source path or run from the source directory.
4. `managed --format=json` is not necessarily structured JSON with the default path style. Verify the exact output shape; v2.70.2 requires `--path-style=all` for the documented keyed structure.
5. Multiple chezmoi processes can contend for persistent-state locks. Do not invoke chezmoi recursively from a chezmoi `run_` script.

## Completion gate

Finish only when the local command surface has been checked, every effect stayed inside the user's scope, secrets and remote writes remained bounded, the requested state is verified, and version or network limitations are reported without being disguised as success.
