# Command and effect reference

Use this reference when exact syntax, output, exit behavior, or mutation boundaries matter. Run `chezmoi <command> --help` on the installed binary before using a flag that may have changed.

## Daily command map

| Intent | Command form | Primary effect | Reliable check |
|---|---|---|---|
| Show installed contract | `chezmoi --version` | none | capture version/build output |
| Locate state | `chezmoi source-path`; `chezmoi target-path` | none | returned paths match intended roots |
| List drift | `chezmoi status [target...]` | none on destination | interpret both status columns |
| Show rendered difference | `chezmoi diff [target...] --no-pager` | none on destination | inspect stdout; difference does not imply nonzero exit |
| Check convergence | `chezmoi verify [target...]` | none on destination | 0 means match; 1 means mismatch |
| Capture target in source | `chezmoi add [flags] target...` | source write | inspect source path and source Git diff |
| Edit source for a target | `chezmoi edit target...` | source write | run `diff`, then optionally `apply` |
| Capture destination edits | `chezmoi re-add [target...]` | source write | not for templates; inspect source diff |
| Apply desired state | `chezmoi apply [target...]` | target write and possible scripts | preview, apply, then `verify` |
| Pull and apply | `chezmoi update` | local Git/source plus target | prefer separated review flow |
| Pull without applying | `chezmoi update --apply=false` | local Git/source | inspect source Git state and `chezmoi diff` |
| Render a target | `chezmoi cat target...` | template evaluation | compare output without printing secrets publicly |
| Inspect template data | `chezmoi data [--format=json|yaml]` | template/data evaluation | validate expected keys and keep values private |
| Test template text | `chezmoi execute-template 'template'` | template evaluation | inspect rendered stdout |
| Diagnose setup | `chezmoi doctor --no-network` | local checks | classify warnings and failures |

## Common review controls

- `--dry-run` prevents destination modification. It does not promise that source, config, hooks, Git, or network dependencies remain untouched.
- `--verbose` shows approximate actions and unified file diffs.
- `--exclude=scripts` keeps chezmoi scripts out of a preview or apply; it does not disable configured hooks.
- `--refresh-externals=never` avoids refreshing an existing externals cache, but missing cached data can still require a download.
- `--no-pager`, `--no-tty`, `--color=off`, and `--progress=false` help automation, but non-interactive conflict behavior must still be designed explicitly.
- `--source` and `--destination` select alternate roots. For isolated tests, also override config, cache, and persistent state.

## Output and exit semantics

### `status`

The first column compares the actual target with the last state chezmoi wrote. The second compares the actual target with desired target state and describes what `apply` would do. `A`, `D`, `M`, and `R` mean add, delete, modify, and run.

### `diff`

Treat stdout as the observable. The exercised v2.70.2 binary returned 0 while showing differences, and its global `--output` did not redirect this command. Capture stdout with `--no-pager` rather than assuming output-file behavior.

### `verify`

Returns 0 when every selected target matches and 1 when any does not. Use this command for CI drift checks; do not treat a 1 as infrastructure failure until the output and context show why it mismatched.

### Structured listings

Do not assume a `--format=json` flag always creates a JSON document. For v2.70.2, `managed --format=json` with relative path style still emitted newline-separated paths; `--path-style=all` produced a keyed structure. Parse only a locally verified shape.

## Version boundary

The local verification binary was v2.70.2. The official v2.71.0 release added global `--error-on-conflict` and init `--revision`/`--tag`, and current docs use `-w` for `--working-tree` where v2.70.2 help showed `-W`. Gate these through local help instead of copying current docs into an older invocation.

When an unfamiliar binary or upgrade needs a repeatable contract check, run:

```sh
python3 scripts/probe_chezmoi.py
python3 scripts/probe_chezmoi.py --integration
```

The first command reads version and help only. `--integration` also exercises add, status, diff, drift verification, dry-run apply, real apply, and clean verification with independent temporary source, destination, config, cache, and persistent state. It never uses ambient chezmoi state or the caller's dotfiles.

## Sources

- [Official commands](https://www.chezmoi.io/reference/commands/)
- [Global flags](https://www.chezmoi.io/reference/command-line-flags/global/)
- [Common flags](https://www.chezmoi.io/reference/command-line-flags/common/)
- [v2.71.0 release](https://github.com/twpayne/chezmoi/releases/tag/v2.71.0)

## See also

- `references/daily-workflows.md` for ordered daily loops
- `references/recovery-and-safety.md` for conflicts, locks, and destructive commands
- `references/official-documentation.md` for refreshing current evidence
