# Daily workflows

Use these flows for ordinary inspection, editing, capture, application, and synchronization. Keep target arguments narrow and preserve the core inspect → preview → apply → verify order.

Before a source or target mutation, capture `chezmoi --version`; command examples below assume the installed help confirms their flags.

## Edit source, then apply

```sh
chezmoi edit ~/.zshrc
chezmoi diff ~/.zshrc --exclude=scripts --no-pager
chezmoi apply --dry-run --verbose --exclude=scripts ~/.zshrc
chezmoi apply --exclude=scripts ~/.zshrc
chezmoi verify --exclude=scripts ~/.zshrc
```

`edit --apply` and `edit --watch` are conveniences that collapse review and target mutation. Use them only when the user asked for that immediacy and understands that each save or editor exit can change the target.

## Capture an existing dotfile

Inspect secrets and destination scope first, then:

```sh
chezmoi add --secrets=error ~/.gitconfig
chezmoi diff ~/.gitconfig --no-pager
```

Use `--template` only when the file actually needs machine-specific rendering. Use `--encrypt` for source-state encryption after the recipient or key path has been verified. Review the source Git diff before committing anything.

## Capture edits made in the destination

For a non-template target:

```sh
chezmoi re-add ~/.config/tool/config
chezmoi diff ~/.config/tool/config --no-pager
```

`re-add` does not update templates. For a templated file, compare the rendered target with the destination and edit or merge the template deliberately.

## Inspect drift without changing target state

```sh
chezmoi status --exclude=scripts
chezmoi diff --exclude=scripts --no-pager
chezmoi verify --exclude=scripts
```

Do not use only the process status from `status` or `diff` as a drift detector. Parse their documented output or use `verify` for the convergence result.

## Pull remote changes for review

Use the official separated workflow when the user wants to inspect before applying:

```sh
chezmoi git pull -- --autostash --rebase
chezmoi diff --exclude=scripts --no-pager
chezmoi apply --dry-run --verbose --exclude=scripts
```

Run the real `apply` only after review. Pulling mutates the local source repository and may contact the network, even though it does not write remote state.

An alternative on supported versions is:

```sh
chezmoi update --apply=false
chezmoi diff --exclude=scripts --no-pager
```

## Pull and apply in one step

```sh
chezmoi update
```

Use this only when the user asked for the combined source and target effect. Afterward, run `status` or `verify` and inspect the source Git state. Do not describe `update` as a preview.

## Work directly in source state

`chezmoi cd` opens a child shell; it cannot change the caller's current directory. For a caller that needs the source path:

```sh
cd "$(chezmoi source-path)"
```

On PowerShell, use a native assignment and `Set-Location` instead of POSIX command substitution.

## Source-path targeting

`--source-path` reinterprets target arguments as source paths. Relative values resolve from the current working directory, so prefer an absolute result from `chezmoi source-path` or change into source state before running the command.

## Completion checks

- The source Git diff contains only intended files and no plaintext secret.
- The target preview contains only intended paths and effect types.
- Scripts and hooks were either deliberately included or explicitly accounted for.
- `verify` or an equivalent content check proves the requested target state.

## Sources

- [Daily operations](https://www.chezmoi.io/user-guide/daily-operations/)
- [Usage FAQ](https://www.chezmoi.io/user-guide/frequently-asked-questions/usage/)
- [Add](https://www.chezmoi.io/reference/commands/add/)
- [Apply](https://www.chezmoi.io/reference/commands/apply/)
- [Update](https://www.chezmoi.io/reference/commands/update/)

## See also

- `references/templates-secrets-and-scripts.md` for templates and sensitive data
- `references/recovery-and-safety.md` for merge and conflict routes
