---
name: ripgrep
description: "Uses ripgrep (`rg`) for local text and path search: code symbols, literals, regexes, filename discovery, machine-readable matches. Use when searching repository files or local logs. Not for web search, reading a known file, or JSON queries better handled by jq."
compatibility: "Requires rg. `-P` needs an rg build with PCRE2 (check `rg --pcre2-version`)."
---

# ripgrep

Use `rg` instead of `grep` for recursive text search, and `rg --files` instead of `find | grep` for path discovery (`rg --files | rg '(^|/)Dockerfile$'`). Fall back to `grep` only when `rg` is missing or exact POSIX behaviour is the requirement. Read a known file directly rather than searching for it. Behaviour below was verified on ripgrep 15.1.0 (2026-04-10); if an example disagrees with the installed build, check `rg --version` and `rg --help`.

## Defaults

- `-F` for literals, especially user-supplied strings with punctuation; single-quote patterns and replacements so the shell does not touch `$1`, `!` or backslashes.
- Narrow early with a path plus `-t type` or `-g glob` (`-T` excludes a type).
- `rg -l` to find files before opening them; `--count-matches` counts matches, `-c` counts matching lines.
- For scripts: `-n --color never --no-heading`, `--json` (JSON Lines: begin/match/end/summary), `-0` or `-l` for file lists, and `--sort path` only when determinism matters (it forces single-threaded search).
- Exit codes: 0 match, 1 no match, 2 error; `-q` when only the code matters.

## Missing results

`rg` skips what is ignored (`.gitignore`, `.ignore`, `.rgignore`, precedence in that reverse order), hidden, binary, and symlinked. Choose the override that matches the suspicion instead of a ladder of retries:

```bash
rg --hidden 'pattern' config/              # hidden, ignores still apply
rg -u 'pattern' logs/                      # ignored, hidden still skipped
rg --hidden --no-ignore 'pattern' .cache/  # both, known subtree
rg -n -F 'needle' .cache/result.txt        # explicit file path overrides ignore and globs
rg --debug 'pattern' src/                  # unknown skip reason
```

`-uuu` also searches binary files; use it only for that. `--no-ignore` does not imply hidden. Later `-g` globs override earlier ones, so `-g '!*.txt' -g '*.txt'` and the reverse differ.

## Gotchas

- `--replace` / `-r` only changes printed output; it never edits files. Use `rg` to locate, then an editor or codemod to write.
- `--json` does not combine with `--files`, `-l`, `-c` or `--count-matches`.
- `-P` (lookaround, backreferences) needs PCRE2 and is slower; `-U` multiline (`-U '(?s)start.*end'`) reads more into memory. Use each only when the match needs it.
- Counts and file lists can disagree on binary-heavy input; rerun with `--binary` or `-a`.
- `rg` is recursive when given directories, and has no PCRE2 by default.

## Configuration

ripgrep reads no config unless `RIPGREP_CONFIG_PATH` points at a file: one argument per line, `#` comments, disabled per command with `--no-config`. Reasonable defaults are `--smart-case`, `--no-heading` for scripts, and a `--type-add=web:*.{html,css,js,jsx,ts,tsx}` style type for languages searched constantly; do not set `--hidden`, `--no-ignore`, `-u`, `-P` or `-U` globally. Inspect types with `rg --type-list`; clear a built-in before redefining it with `--type-clear json --type-add 'json:*.json5'`. Keep aliases transparent (`alias rgl='rg -n -F'`).
