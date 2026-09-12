# ripgrep

Production skill for making `rg` the default search tool instead of `grep`.

## What It Covers

- Recursive text search with literal and regex patterns
- Filename discovery via `rg --files`
- Ignore, hidden, binary, compressed, multiline, and PCRE2 search modes
- Config files, custom types, and shell-friendly automation patterns
- Verified local probes against real `ripgrep` behavior

## Key Files

- `SKILL.md` - authoritative instructions
- `references/commands.md` - command atlas and output modes
- `references/configuration.md` - config files, aliases, custom types, and setup
- `references/patterns.md` - agent workflows and shell pipelines
- `references/gotchas.md` - missing-result and quoting traps
- `scripts/probe_ripgrep.py` - repeatable behavior verification suite

