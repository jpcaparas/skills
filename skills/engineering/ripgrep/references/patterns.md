# Search Patterns and Workflows

Use this file when the task is not “what flag exists?” but “what is the right ripgrep workflow?”

## Prefer Search-Then-Read

Do not read entire trees when the user asked a targeted question.

Recommended loop:

1. Use `rg -n` or `rg -l` to locate the relevant files and lines.
2. Open only the small set of files that actually matter.
3. Refine with more specific `rg` calls if the first search is too broad.

Example:

```bash
rg -n -t py 'RIPGREP_CONFIG_PATH|type-add' .
rg -l -t py 'RIPGREP_CONFIG_PATH|type-add' .
```

## Filename Discovery Without `find | grep`

When the job is path discovery, start with `rg --files`.

```bash
# Dockerfiles and variants
rg --files | rg '(^|/)Dockerfile(\.[^/]+)?$'

# Python test files
rg --files tests/ | rg '(^|/)test_.*\.py$'

# Lockfiles
rg --files | rg '(^|/)(package-lock\.json|pnpm-lock\.yaml|Cargo\.lock)$'
```

This is usually the right replacement for:

```bash
find . -type f | grep ...
```

Use `find` or `fd` only when you need metadata such as mtime, permissions, size, or symlink-specific traversal rules.

## Literal First, Regex Second

If the user gave a concrete string, start literal:

```bash
rg -n -F 'https://api.example.com/v1/users' .
```

Switch to regex only when the task truly needs pattern language:

```bash
rg -n 'https://api\.example\.com/v[0-9]+/users' .
```

This reduces accidental false positives and shell-escaping bugs.

## Narrow Early

Limit the search space before the first expensive scan:

```bash
rg -n -t rs 'unsafe' crates/
rg -n -g '*.sql' 'ALTER TABLE' migrations/
rg -n --max-depth 2 'TODO' docs/
```

Prefer one or more of:

- explicit paths
- `-t` or `-T`
- `-g` or `--iglob`
- `--max-depth`
- `--max-filesize`

## Stable Output for Scripts

When another tool will consume the results, make the output boring and predictable.

```bash
# Simple text output
rg -n --color never --no-heading --sort path 'pattern' .

# JSON output
rg --json 'pattern' .

# NUL-delimited file list
rg -l -0 'pattern' .
```

Use `--sort path` when deterministic order matters for tests, snapshots, or review diffs. Accept the speed tradeoff because sorting disables parallel traversal.

## Automation-Friendly Combinations

```bash
# Count hot spots
rg --count-matches 'TODO|FIXME' . | sort -t: -k2 -rn

# Open only matching files
rg -l 'needle' . | xargs sed -n '1,40p'

# Extract tokens and deduplicate
rg -o '\b[A-Z][A-Z0-9_]{2,}\b' . | sort -u

# Stream logs
tail -f app.log | rg --line-buffered 'ERROR|WARN'

# Drive downstream tooling safely
rg -l -0 'pattern' . | xargs -0 wc -l
```

If downstream tools may choke on spaces or newlines in paths, use `-0` and `xargs -0`.

## Debugging Missing Results

Use a strict escalation path instead of giving up:

```bash
# 1. Normal search
rg -n 'pattern' .

# 2. Hidden files might matter
rg -n --hidden 'pattern' .

# 3. Ignore files might be hiding it
rg -n -u 'pattern' .

# 4. Need to see why ripgrep skipped things
rg --debug 'pattern' .
```

This approach is better than jumping straight to `grep -R` because it preserves speed and teaches you why the match disappeared.

## Large Repositories

For very large trees:

```bash
rg -n -F 'needle' src/
rg -n --max-filesize 1M 'needle' .
rg -l -t go 'context.Context' services/
```

Prefer:

- literal search when possible
- explicit subtrees
- type filters
- file lists before content reads

Avoid:

- `-uuu` by reflex
- multiline search unless necessary
- path sorting unless reproducibility matters

## Code Review and Refactor Support

Use `rg` to answer questions before editing:

```bash
# Find all call sites
rg -n 'renderInvoice\(' src/

# Find imports
rg -n 'from .*invoice' -t ts src/

# Find TODO or FIXME comments
rg -n '(TODO|FIXME|HACK|XXX):' .

# Preview renamed identifier in output only
rg -n '\bold_name\b' -r 'new_name' src/
```

Use `-l` when you only need the affected file set and will inspect the files afterward.

## Documents, Logs, and Data Dumps

Ripgrep is not just for code:

```bash
# Paragraph-style context in docs
rg -C 2 'latency budget' docs/

# Structured log hunting
rg -n 'request_id=abc123|trace_id=abc123' logs/

# Search compressed logs
rg -z 'panic|ERROR' logs/archive/

# Search over multiple lines
rg -U '(?s)BEGIN EXCEPTION.*END EXCEPTION' logs/
```

Use `-a` only when you consciously want binary-as-text behavior.

## See Also

- Read `references/commands.md` for the exact flags in each example.
- Read `references/configuration.md` to make a pattern repeatable with config or aliases.
- Read `references/gotchas.md` when an otherwise sensible workflow returns surprising output.

