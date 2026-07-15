# Recovery and safety

Use this reference when the target, desired state, last-written state, or source history disagree; when locks or scripts fail; or when a removal command is requested.

## Diagnose the state owner

Run:

```sh
chezmoi --version
chezmoi doctor --no-network
chezmoi status --exclude=scripts
chezmoi diff --exclude=scripts --no-pager
```

Interpret `status` before choosing a direction. The first column describes actual changes since chezmoi last wrote the target; the second describes what `apply` would change to reach desired state.

## Resolve destination and source changes

- Destination change should win, non-template target: `re-add TARGET`, then inspect source diff.
- Source state should win: preview and run scoped `apply TARGET`.
- Both contain useful changes: `merge TARGET` or `merge-all`, then inspect both rendered and source diffs.
- Templated target: edit or merge the template; `re-add` does not overwrite it.

Do not use `--force` as a conflict strategy. On v2.71.0+, `--error-on-conflict` can make automation fail closed after local help confirms the flag. Older binaries should stop or use an intentional interactive resolution.

## Persistent-state lock timeouts

Write-lock commands include add, apply, edit, forget, import, init, state, unmanage, and update. Diff, status, and verify take read locks. When a lock times out:

1. Find another running chezmoi process or recursive invocation.
2. Stop or wait for the legitimate owner rather than deleting state immediately.
3. Inspect `run_` scripts for nested chezmoi calls.
4. Retry one scoped read after the owner exits.

Do not delete the persistent-state database unless official recovery guidance and a backup justify it.

## Removal vocabulary

| Command | Intended outcome | Required safeguard |
|---|---|---|
| `forget` / `unmanage` | remove source management, leave target | verify source diff and target preservation |
| `.chezmoiremove` | remove matched targets during apply | dry-run verbose; inspect every pattern and negative match |
| `destroy` | permanently remove both source and target | independent backup, exact targets, explicit confirmation |
| `purge` | remove chezmoi config, state, and source while leaving target state | backup source/config and verify targets remain |

Use the local help because aliases and prompts can change. Never infer `destroy` from a request to “stop managing” a file.

## Script and hook failures

- A failed `run_once_` or `run_onchange_` can be eligible to run again; inspect its state and output before redriving.
- Scripts can fail on `noexec` temporary filesystems or a shebang displaced by template whitespace.
- Hooks run even under `--dry-run`; inspect configured hooks when a supposedly safe preview still has effects.
- Keep retries bounded and only for idempotent actions.

## Completion checks

- The chosen recovery direction—source wins, target wins, or merge—is explicit.
- Backups exist before any irreversible cleanup.
- No concurrent lock owner remains unexplained.
- Target, source, and persistent state agree with the requested postcondition.

## Sources

- [Troubleshooting FAQ](https://www.chezmoi.io/user-guide/frequently-asked-questions/troubleshooting/)
- [Merge](https://www.chezmoi.io/reference/commands/merge/)
- [Forget](https://www.chezmoi.io/reference/commands/forget/)
- [Destroy](https://www.chezmoi.io/reference/commands/destroy/)
- [Purge](https://www.chezmoi.io/reference/commands/purge/)

## See also

- `references/commands.md` for exit and output semantics
- `references/templates-secrets-and-scripts.md` for script lifecycle
