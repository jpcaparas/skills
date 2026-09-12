# Templates, secrets, and scripts

Use this reference when source state needs computation, sensitive values, encryption, or effectful scripts. Test rendering separately from application.

## Build and debug templates

A file is templated when its source name ends in `.tmpl` or it lives under `.chezmoitemplates/`.

Inspect data and test a small expression:

```sh
chezmoi data --format=yaml
chezmoi execute-template '{{ .chezmoi.os }}/{{ .chezmoi.arch }}'
```

Test a full template through stdin or the locally documented `--file` option, then inspect its target with `chezmoi cat`. Keep rendered secrets out of shared logs.

Data is assembled in order: chezmoi built-ins under `.chezmoi`, `.chezmoidata` files in documented order, then config `data`; later sources overwrite earlier ones. Put portable defaults in source data and machine-specific values in local config.

## Create or convert a template

```sh
chezmoi add --template ~/.gitconfig
chezmoi chattr +template ~/.zshrc
```

`--autotemplate` can make greedy substitutions. Treat its output as a draft and require a source diff plus rendered preview before applying it.

If a template renders empty, chezmoi removes the target. Use the `empty_` source attribute only when an empty file is the intended state.

## Keep secrets out of source history

Choose one of these boundaries:

1. Password-manager functions in templates for secrets resolved at apply time.
2. Encrypted source entries, after the age/GPG recipient and recovery material are verified.
3. Local config data that is deliberately absent from version control.

Use secret scanning when adding ordinary files:

```sh
chezmoi add --secrets=error TARGET
```

`chezmoi add --encrypt TARGET` creates encrypted source state, but encryption is only safe when recipients, keys, and recovery are configured and tested. `chezmoi edit` transparently decrypts and re-encrypts encrypted source entries; avoid copying its temporary plaintext into logs or unrelated paths.

## Script behavior

- `run_` executes on every apply.
- `run_onchange_` executes when rendered contents change after a successful prior run.
- `run_once_` executes once for each unique rendered-content version.
- `before_` and `after_` control phase; scripts run in alphabetical order within their phase.

Prefer idempotent scripts with explicit timeouts and stable observable outcomes. Put a template script's shebang at byte zero; whitespace before `#!` can cause an exec-format error.

Dry-run mode does not execute chezmoi scripts, but configured hooks still run. A preview using `--exclude=scripts` also excludes script target entries; it does not disable hooks or arbitrary effects inside template functions.

Do not invoke chezmoi recursively from a `run_` script. Persistent-state locking can deadlock or time out the nested command.

## Completion checks

- Template syntax and data keys render successfully for each affected machine class.
- No plaintext secret appears in source state, command output, diffs, logs, or eval fixtures.
- Script identity, ordering, repeat behavior, timeout, and idempotency are explicit.
- Preview and post-apply checks account for hooks, externals, and password-manager access.

## Sources

- [Templating](https://www.chezmoi.io/user-guide/templating/)
- [Password managers](https://www.chezmoi.io/user-guide/password-managers/)
- [Encryption](https://www.chezmoi.io/user-guide/encryption/)
- [Scripts](https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/)
- [Hooks](https://www.chezmoi.io/reference/configuration-file/hooks/)

## See also

- `references/setup-and-machines.md` for portable versus local data
- `references/recovery-and-safety.md` for script failures and state locks
