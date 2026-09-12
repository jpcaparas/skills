# ripgrep Gotchas

Use this file when a command looks correct but the result set is missing matches, output looks strange, or a shell ate part of the pattern.

## `rg` Is Not POSIX `grep`

Ripgrep is the preferred search tool for most recursive search work, but it is not a bug-for-bug clone of GNU or POSIX `grep`.

Relevant differences:

- It respects ignore files by default.
- It skips hidden files and binary files by default.
- It is recursive by default when given directories.
- Its default regex engine is not PCRE2.

Use `grep` only when the environment lacks `rg` or when exact POSIX grep behavior is the actual requirement.

## Missing Results Usually Mean Filtering

By default, ripgrep filters:

- `.gitignore`
- `.ignore`
- `.rgignore`
- hidden files and directories
- binary files
- symlink targets

Recommended escalation:

```bash
rg 'pattern' .
rg --hidden 'pattern' .
rg -u 'pattern' .
rg --debug 'pattern' .
```

Do not jump straight to `-uuu` unless the problem statement actually justifies it.

## Ignore Precedence Can Be Non-Obvious

Upstream documents this precedence:

1. `.rgignore`
2. `.ignore`
3. `.gitignore`

That means a file whitelisted in `.ignore` can still be suppressed again in `.rgignore`.

Also remember:

- Explicit file paths on the command line override ignore and glob rules.
- `--no-ignore` drops ignore-file filtering, but does not automatically imply hidden or binary search.

## Glob Order Matters

Later globs override earlier ones.

```bash
rg 'TODO' -g '!*.txt' -g '*.txt' .
rg 'TODO' -g '*.txt' -g '!*.txt' .
```

Those two commands do not mean the same thing. If a seemingly reasonable glob pair yields no matches, check the order first.

## Shell Quoting Is a Real Failure Mode

Common traps:

- Double quotes allow `$1` in replacement strings to be expanded by the shell.
- History expansion can bite on `!` in some shells.
- Backslashes can disappear before ripgrep sees the pattern.

Prefer single quotes:

```bash
rg -P '(?<=prefix)value(?=suffix)' .
rg 'fast\s+(\w+)' README.md -r 'fast-$1'
```

## `-P` and `-U` Are Not Free

`-P` requires a build compiled with PCRE2. Even when available, it is not the fastest option.

`-U` enables multiline matching. That can cause ripgrep to read more data into memory and behave much less like its fast line-oriented default.

Prefer:

- default engine for ordinary regexes
- `-F` for literals
- `-P` only for lookaround or backreferences
- `-U` only when the match truly spans lines

## `--replace` Does Not Edit Files

This flag only changes stdout.

```bash
rg 'old_name' -r 'new_name' src/
```

If the task is a real edit, use ripgrep to locate the matches and then use an editor, codemod, `sed`, or another write-capable tool.

## `-c` vs `--count-matches`

- `-c` counts matching lines
- `--count-matches` counts individual matches

If one line contains three matches, `-c` reports `1` while `--count-matches` reports `3`.

## `--json` Is Powerful but Narrow

`--json` emits search results as JSON Lines and implicitly enables stats, but it does not combine with:

- `--files`
- `-l`
- `--files-without-match`
- `-c`
- `--count-matches`

If you need a file list, use `-l` or `--files`. If you need structured match data, use `--json`.

## Sorting Costs Speed

`--sort path` and `--sortr path` produce deterministic traversal, but they also force single-threaded behavior. Use sorting for reproducibility, not by default.

## Binary and Counting Can Disagree

Ripgrep may stop early or treat files differently depending on the output mode when binary data is involved. If counts and file lists disagree on binary-heavy inputs, re-run with `--binary` or `-a` and compare again.

## See Also

- Read `references/commands.md` for exact flag syntax.
- Read `references/patterns.md` for escalation workflows and script-friendly pipelines.
- Read `references/configuration.md` when the same gotcha keeps repeating and you need better defaults.

