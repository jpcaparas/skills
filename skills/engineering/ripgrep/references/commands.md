# ripgrep Command Atlas

Use this file when you need exact `rg` flags, output modes, or search semantics.

## Search Basics

Start with the narrowest command that answers the question.

```bash
# Literal string, safest default for user text
rg -n -F 'api.example.com' src/

# Regex search
rg -n 'foo\s+bar' src/

# Pattern begins with a dash
rg -n -e '-foo' .

# Search stdin
git diff --name-only | rg '\.py$'
```

Prefer single quotes around patterns in shells like `bash` and `zsh`. That protects backslashes, `$1`, and `!` from shell expansion.

## Case and Match Shape

```bash
# Always case-sensitive
rg -s 'Token' .

# Always case-insensitive
rg -i 'token' .

# Lowercase patterns become case-insensitive
rg -S 'token' .

# Whole-word match
rg -w 'token' .

# Entire line must match
rg -x 'token=.*' .env

# Invert matching lines
rg -v '^#' config.ini

# Limit matching lines per file
rg -m 5 'ERROR' logs/
```

Use `-F` whenever the user hands you a literal string containing dots, brackets, question marks, or other regex punctuation. That avoids accidental regex behavior and is usually faster.

## File Selection

### Explicit paths

```bash
rg -n 'pattern' src/ tests/
rg -n 'pattern' path/to/file.py
```

Explicit file paths on the command line override ignore rules and glob filters. Use this when the user named the file already.

### File types

```bash
rg -n -t py 'def main' .
rg -n -t ts -t tsx 'useEffect' src/
rg -n -T test 'render' src/
rg --type-list
```

Use `-t` to include file types and `-T` to exclude them. Prefer `-t` over large glob lists when built-in or custom types already express the constraint.

### Globs

```bash
rg -n -g '*.tsx' 'Component' src/
rg -n -g 'src/**' -g '!src/generated/**' 'TODO' .
rg -n --iglob '*.JSON' 'schema' .
```

Globs follow `.gitignore` syntax. Later `-g` flags override earlier ones. That matters:

```bash
# Matches only *.txt
rg 'TODO' -g '!*.txt' -g '*.txt' .

# Matches nothing
rg 'TODO' -g '*.txt' -g '!*.txt' .
```

### Filename discovery

```bash
# All searchable files
rg --files

# Only under a subtree
rg --files src/

# Filter the file list with a second rg
rg --files | rg '(^|/)Dockerfile(\.[^/]+)?$'

# Safe for xargs
rg --files -0 | xargs -0 sed -n '1,5p'
```

Use `rg --files` when the task is path discovery. It is usually the right replacement for `find . | grep ...` when you do not need filesystem metadata.

## Hidden, Ignored, Binary, and Special Data

```bash
# Include hidden files and directories
rg --hidden 'secret' .

# Disable ignore-file filtering
rg -u 'pattern' .
rg --no-ignore 'pattern' .

# Disable ignore filtering and include hidden files
rg -uu 'pattern' .

# Disable ignore, hidden, and binary filtering
rg -uuu 'pattern' .

# Search binary as text
rg -a 'needle' artifact.bin

# Search compressed files
rg -z 'panic' logs/app.log.gz

# Specify encoding
rg -E shift_jis '検索語' docs/
```

Escalate these deliberately. Most missing-match complaints are solved by `--hidden`, `-u`, or `--debug`.

## Output Modes

```bash
# Files containing a match
rg -l 'TODO' .

# Files with zero matches
rg --files-without-match 'TODO' .

# Count matching lines per file
rg -c 'TODO' .

# Count individual matches per file
rg --count-matches 'TODO' .

# Print only the matching part
rg -o '[A-Z]{2,}' README.md

# Editor-friendly format
rg --vimgrep 'pattern' .

# JSON Lines output
rg --json 'pattern' .

# Deterministic path ordering
rg --sort path 'pattern' .

# Include statistics
rg --stats 'pattern' .
```

Use `--json` for automation. Use `--sort path` only when deterministic order matters more than speed, because sorting disables parallel traversal.

## Context and Preview

```bash
rg -A 3 'panic' app.log
rg -B 2 'panic' app.log
rg -C 2 'panic' app.log
rg --passthru 'panic' app.log
```

`--passthru` prints both matching and non-matching lines while still highlighting matches. It is useful for lightweight preview workflows.

## Regex Engines

```bash
# Default engine
rg 'foo(bar|baz)' .

# PCRE2 explicitly
rg -P '(?<=prefix)value(?=suffix)' .

# Auto-select engine based on pattern features
rg --engine auto '(?<=prefix)value(?=suffix)' .
```

Use the default engine unless you need lookaround or backreferences. PCRE2 is powerful, but it is not guaranteed to exist in every build and can be slower.

## Multiline Search

```bash
# Search across line boundaries
rg -U '(?s)start.*end' multi.txt

# Enable dotall globally once multiline is on
rg -U --multiline-dotall 'start.*end' multi.txt

# Match a function signature that spans lines
rg -U 'function\s+\w+\([^)]*\)\s*\{' src/
```

Multiline mode can force ripgrep to read more data into memory. If the match should fit on one line, do not turn on `-U`.

## Replacement Preview

```bash
# Preview replacement in output only
rg 'old_name' -r 'new_name' src/

# Replace only the matched token
rg 'fast\s+(\w+)' README.md -r 'fast-$1'

# Replace the whole line by matching the whole line
rg '^.*TODO.*$' todo.txt -r 'DONE'
```

Ripgrep never edits files. `-r` changes stdout only.

## Preprocessors

```bash
# Run a preprocessor only for PDFs
rg --pre ./scripts/pre-pdftotext --pre-glob '*.pdf' 'invoice' docs/
```

Use preprocessors when the real text lives behind a conversion step. This is a last-mile capability, not the default workflow.

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | At least one match found |
| `1` | No matches found |
| `2` | Error occurred |

Use `-q` when only the exit code matters:

```bash
if rg -q 'needle' file.txt; then
  echo "found"
fi
```

## See Also

- Read `references/configuration.md` for `RIPGREP_CONFIG_PATH`, custom file types, and reusable defaults.
- Read `references/patterns.md` for filename discovery, deterministic pipelines, and agent workflows.
- Read `references/gotchas.md` when matches disappear or flags interact in surprising ways.

