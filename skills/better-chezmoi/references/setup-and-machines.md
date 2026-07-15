# Setup and machines

Use this reference for first-time initialization, new machines, containers, or differences across hosts. Keep the portable repository in source state and machine-local values in the local config unless the user deliberately chooses another boundary.

## Inspect before init

Confirm:

- the installed chezmoi version and init help
- source and destination paths
- repository URL, branch, tag, or revision
- whether the destination may be changed now
- authentication requirements for a private repository
- how secrets and local-only data will be supplied

`init` can create source Git state even with `--dry-run`. Use a disposable source directory to evaluate unfamiliar init options.

## Initialize without applying

```sh
chezmoi init REPOSITORY
chezmoi diff --exclude=scripts --no-pager
```

Use locally documented flags such as `--branch`, `--depth`, or `--ssh` only after checking `chezmoi init --help`. The current v2.71.0 docs add `--revision` and `--tag`; older binaries do not necessarily accept them.

## Initialize and apply

```sh
chezmoi init --apply REPOSITORY
```

This combines source setup and destination mutation. Use it when the user requested a bootstrap, not as a default inspection route. A one-shot bootstrap is intended for transitory environments and removes chezmoi's source/config traces afterward; explain that lifecycle before using it.

## Separate portable and machine-local data

The usual model is:

- source directory: version-controlled, shared across machines
- config file: machine-local data and preferences
- templates: render shared source through machine context
- password manager or encrypted source: sensitive values

Inspect available built-ins with:

```sh
chezmoi data
chezmoi execute-template '{{ .chezmoi.os }}/{{ .chezmoi.arch }}/{{ .chezmoi.hostname }}'
```

Prefer `.chezmoi.os`, `.chezmoi.arch`, or deliberately named config data over ad hoc hostname tests when the real distinction is operating system, role, or ownership.

## Exclude machine-specific targets

Use a templated `.chezmoiignore` for coarse file or directory selection. Preview with `chezmoi ignored` and `chezmoi diff` on every affected machine class. A template that renders to empty content removes its target unless the source carries the `empty_` attribute.

## Cross-platform command forms

- Keep paths quoted.
- Use the target shell's native environment-variable and command-substitution syntax.
- Do not assume `~`, POSIX permissions, or executable bits behave identically on Windows.
- Check the official Windows machine guide before writing Windows-specific source attributes, path rules, or shell scripts.

## Completion checks

- Init created the intended source/config state and no unexpected target write.
- Repository identity and revision match the requested source.
- Machine-local values remain outside shared history unless intentionally templated.
- Every supported machine class can render and preview its intended targets.

## Sources

- [Setup](https://www.chezmoi.io/user-guide/setup/)
- [Init command](https://www.chezmoi.io/reference/commands/init/)
- [Machine-to-machine differences](https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/)
- [Windows machines](https://www.chezmoi.io/user-guide/machines/windows/)

## See also

- `references/templates-secrets-and-scripts.md` for the rendering and secret boundary
- `references/official-documentation.md` for current init flags
