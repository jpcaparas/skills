# Configuration and Setup

Use this file when you need repeatable ripgrep behavior across sessions, shells, or machines.

## Confirm the Binary and Feature Set

Run these checks first when a command behaves differently than expected:

```bash
rg --version
rg --pcre2-version
rg --type-list | head
```

Key things to confirm:

- The ripgrep version is recent enough for the flags you plan to use.
- PCRE2 exists before recommending `-P` or `--engine auto` for lookaround and backreferences.
- The expected built-in file types exist before depending on `-t some-type`.

## Config Files

Ripgrep does not automatically scan fixed config locations. You opt into a config file by setting `RIPGREP_CONFIG_PATH`.

```bash
export RIPGREP_CONFIG_PATH="$HOME/.ripgreprc"
rg 'pattern' .
```

Config file rules:

1. Each non-empty line is treated as one shell argument after trimming whitespace.
2. Lines starting with `#` are comments.

Example `~/.ripgreprc`:

```text
# Lowercase queries become case-insensitive.
--smart-case

# Shared frontend bundle.
--type-add=web:*.{html,css,js,jsx,ts,tsx}

# Script-friendly output by default.
--no-heading
```

Disable config-file loading for one command with:

```bash
rg --no-config 'pattern' .
```

Use `templates/ripgreprc.example` as a starting point.

## Custom File Types

Custom types let you replace long glob bundles with a short `-t` flag.

```bash
rg --type-add 'web:*.{html,css,js,jsx,ts,tsx}' -t web 'render' src/
rg --type-add 'proto:*.proto' -t proto 'message ' api/
```

Inspect the resulting definition:

```bash
rg --type-add 'web:*.{html,css,js,jsx,ts,tsx}' --type-list | rg '^web:'
```

Clear a built-in type before redefining it:

```bash
rg --type-clear json --type-add 'json:*.json5' --type-list | rg '^json:'
```

## Shell Aliases

Prefer small, legible aliases over giant wrappers that hide important flags.

Sample aliases live in `templates/rg-aliases.sh`.

Useful patterns:

```bash
alias rgl='rg -n -F'
alias rgf='rg --files'
alias rgj='rg --json --color never --no-heading'
```

Keep aliases transparent. The point is to save keystrokes, not to make commands impossible to reason about.

## Output Defaults for Humans vs Scripts

Default output differs between TTY and non-TTY contexts. For repeatable automation, be explicit:

```bash
rg -n --color never --no-heading 'pattern' .
rg --json 'pattern' .
rg --sort path -n --color never --no-heading 'pattern' .
```

Use human-oriented defaults for local inspection and machine-oriented defaults for scripts.

## Recommended Defaults

These defaults are usually helpful:

- `--smart-case`: lowercase queries become case-insensitive; uppercase literals stay case-sensitive.
- `--no-heading` in scripts: easier to parse than grouped headings.
- One or two custom `--type-add` rules for the languages or document bundles you search constantly.

Avoid setting these as global defaults unless you know you want them nearly always:

- `--hidden`
- `--no-ignore`
- `-u`, `-uu`, `-uuu`
- `-P`
- `-U`

Those flags change semantics enough that they are better chosen per command.

## Platform Notes

- Use single quotes in POSIX shells for patterns and replacement strings.
- On shells with history expansion, `!` inside globs or regex can surprise you if you use double quotes.
- `--path-separator` exists for unusual environments, but most users should leave it alone.

## Verification Workflow

When documenting or automating a config setup:

1. Run `rg --version`.
2. Create a config file with one argument per line.
3. Set `RIPGREP_CONFIG_PATH`.
4. Verify the behavior with a cheap command like `rg --type-list`, `rg 'literal' file`, or `rg --debug`.

Example:

```bash
tmpdir="$(mktemp -d)"
cat >"$tmpdir/rg.conf" <<'EOF'
# demo
--smart-case
--type-add=web:*.{html,css,js}
EOF

RIPGREP_CONFIG_PATH="$tmpdir/rg.conf" rg --type-list | rg '^web:'
```

## See Also

- Read `references/commands.md` for the flags a config file can set.
- Read `references/patterns.md` for workflows that benefit from predictable defaults.
- Read `references/gotchas.md` for quoting and PCRE2 pitfalls.

