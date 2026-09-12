# Filesystem and Read Surface

Prefer path discovery and targeted excerpts over dumping files blindly.

## Escalation Ladder

1. Start with top-level inventory.
2. Move to capped directory shape.
3. Discover candidate paths without reading contents.
4. Search file contents only after path discovery narrowed the field.
5. Read only the slice you need.
6. Parse structured output with `jq` only after the command surface is already small.

## Quick Reference

| Situation | Preferred command | Escalate to | Why |
| --- | --- | --- | --- |
| Need the names in the current directory | `ls -1` | `ls -lah` | Plain names are often enough |
| Need directory structure | `tree -L 2 path/` | `tree -a -L 3 path/` | Depth limits keep output legible |
| Need every tracked-looking path | `rg --files path/` | `rg --files path/ \| rg 'pattern'` | File lists are cheaper than content scans |
| Need files containing a literal | `rg -n -F 'needle' path/` | `rg -n 'regex' path/` | Literal search avoids accidental regex cost |
| Need only matching filenames | `rg -l 'needle' path/` | `rg --files path/ \| rg 'pattern'` | Get the candidate set before opening anything |
| Need the first lines of a file | `sed -n '1,80p' file` | `head -n 120 file` | Line ranges are explicit and cheap |
| Need the last lines of a log | `tail -n 80 file` | `tail -n 200 file` | Pull recent context only |
| Need JSON field extraction | `command \| jq -r '.field'` | `command \| jq '.'` | Raw strings are easier to reuse |

## Harness-Native Tools

If the harness exposes native search or targeted read tools, prefer those before shelling out. They usually return only the relevant lines and avoid shell quoting overhead.

Use shell commands when:

- You need to compose with other shell tools
- You need output formats the harness tool does not expose
- You need to verify behavior that the skill itself documents

## Path Discovery Patterns

### Find filenames before reading files

```bash
rg --files src/ | rg 'service|controller'
```

### Search literals with line numbers

```bash
rg -n -F 'TODO:' .
```

### Search hidden or ignored files only when the missing-result hypothesis justifies it

```bash
rg --hidden -n -F 'SECRET' .
rg -u -n -F 'SECRET' .
rg --debug -n -F 'SECRET' .
```

## Targeted Read Patterns

Use the narrowest read that still answers the question:

```bash
sed -n '1,40p' pyproject.toml
sed -n '120,220p' app/models/user.rb
head -n 60 README.md
tail -n 80 logs/app.log
```

Only reach for a full-file read when:

- The file is already known to be short
- You need global context such as import ordering, config inheritance, or end-to-end flow
- Repeated partial reads would cost more than one full pass

## When Not to Optimize Further

Stop compressing when the user explicitly asked for the full contents of a short file or when a targeted excerpt is hiding the real relationship between sections.

See `references/patterns.md` for fallback choices and `references/gotchas.md` for missing-result traps.
