---
name: ripgrep
description: "Prefer ripgrep (`rg`) for text search, recursive codebase search, filename discovery with `rg --files`, and machine-readable search output. Trigger on search, grep, ripgrep, rg, find files, or look for pattern. Do NOT use for full-file reads or JSON queries better handled by jq."
compatibility: "Requires: rg. Optional: python3 for probe and validation scripts. PCRE2-specific patterns require an rg build compiled with PCRE2."
metadata:
  version: "1.0.0"
  short-description: "Prefer rg over grep for fast recursive search"
  openclaw:
    category: "development"
    subcategory: "search"
    requires:
      bins: [rg, python3]
    cliHelp: "rg --help"
    tags: ["ripgrep", "rg", "grep", "search", "codebase", "regex"]
references:
  - commands
  - configuration
  - patterns
  - gotchas
---

# ripgrep

Prefer `rg` over `grep` for text search, and prefer `rg --files` over `find | grep` when the real task is path discovery.

Verified locally against `ripgrep 15.1.0` on April 10, 2026. The skill is repo-agnostic, but the examples assume a Unix-like shell and an `rg` binary in `PATH`.

## Decision Tree

What kind of search do you need?

- Search file contents for text, symbols, regexes, or literals
  - Start with `rg`
  - Read `references/commands.md`

- Find filenames or paths without reading file contents
  - Start with `rg --files [path]`
  - Then filter that list with a second `rg` if needed
  - Read `references/patterns.md`

- Search only specific languages, globs, hidden files, ignored files, compressed data, or multiline blocks
  - Read `references/commands.md`
  - If results seem wrong or missing, read `references/gotchas.md`

- Make ripgrep behavior repeatable with config files, aliases, or custom file types
  - Read `references/configuration.md`

- Feed results into automation, scripts, editors, or other tools
  - Prefer `--json`, `-0`, `-l`, `--count-matches`, or `--sort path` as appropriate
  - Read `references/patterns.md`

- The user wants full-file reading, structured JSON queries, or filesystem metadata
  - Do not force `rg` into a role it is bad at
  - Read the file directly, or use `jq`, `find`, or `fd`

## Default Operating Rules

1. Use `rg` first for text search. Only fall back to `grep` when `rg` is unavailable or exact POSIX grep behavior is the real requirement.
2. Use `-F` for user-provided literals unless the user clearly asked for regex semantics.
3. Narrow the search early with an explicit path plus `-t` or `-g` instead of searching the entire tree and cleaning up later.
4. Use `rg --files` for path discovery, then pipe into another `rg` for filename filtering instead of composing `find ... | grep ...`.
5. Escalate ignore overrides gradually: normal search, then `--hidden`, then `-u` or `--no-ignore`, then `-uu` or `-uuu` only if the missing-result hypothesis justifies it.
6. Use `--debug` when results are missing and you need to know what ripgrep skipped.
7. Use `--json` or `-n --color never --no-heading` for machine consumption. Prefer `--sort path` when deterministic output matters more than maximum speed.

## Quick Reference

| Need | Command | Notes |
| --- | --- | --- |
| Literal text search | `rg -n -F 'needle' path/` | Best default for user-provided strings with punctuation |
| Regex search | `rg -n 'foo\\s+bar' path/` | Use single quotes so the shell does not interfere |
| Filenames only | `rg --files path/` | Respects ignore files by default |
| Filter filenames | `rg --files | rg '(^|/)Dockerfile$'` | Good replacement for `find . | grep ...` |
| Match specific languages | `rg -n -t py 'pattern' src/` | `-t` includes, `-T` excludes |
| Match specific globs | `rg -n -g '*.tsx' 'pattern' src/` | Later globs override earlier ones |
| Search hidden or ignored content | `rg --hidden 'pattern'` then `rg -u 'pattern'` | Escalate only as needed |
| Files with matches | `rg -l 'pattern' path/` | Use before opening files |
| Count individual matches | `rg --count-matches 'pattern' path/` | `-c` counts matching lines, not matches |
| Machine-readable output | `rg --json 'pattern' path/` | Best for tools and scripts |
| Lookaround or backreferences | `rg -P '...' path/` | Requires PCRE2 support in the build |
| Multiline blocks | `rg -U '(?s)start.*end' file` | Multiline is slower and more memory-hungry |
| Diagnose skipped files | `rg --debug 'pattern' path/` | Shows ignore and skip reasons |

## Reading Guide

| Task | Read |
| --- | --- |
| Correct command, flag, or output mode | `references/commands.md` |
| Config files, aliases, custom types, and environment setup | `references/configuration.md` |
| Agent search workflows, filename discovery, shell pipelines, and deterministic output | `references/patterns.md` |
| Missing results, quoting issues, multiline surprises, JSON limits, and other traps | `references/gotchas.md` |

## Verified Behaviors

1. `rg --files` respects ignore rules by default and excluded an ignored `logs/app.log` in local probes.
2. `.rgignore` overrode `.ignore`, and `--no-ignore` restored access to the same ignored file.
3. `--hidden` surfaced hidden content without turning off ignore handling.
4. The order of `-g` flags changed the result set exactly as upstream documents: later globs overrode earlier ones.
5. `RIPGREP_CONFIG_PATH` successfully loaded `--smart-case` and a custom `web` type from a config file.
6. `--json` emitted `begin`, `match`, `end`, and `summary` messages in JSON Lines format.
7. `-U '(?s)...'` matched across lines, and `-P` lookaround worked on this machine because the local build includes PCRE2.

## Gotchas

1. `rg` is not a byte-for-byte drop-in replacement for POSIX `grep`; it is the default search tool when speed, recursion, ignore handling, or Unicode-aware regex matter.
2. Missing results are usually an ignore, hidden-file, glob-order, or quoting problem before they are a ripgrep bug. Run `--debug` before switching tools.
3. `--replace` changes printed output only. It never edits files.
4. `--json` is for search results, not every output mode. It does not combine with `--files`, `-l`, or `-c`.
5. `-P` and `-U` are powerful but costlier than the default engine and normal line-oriented search. Use them deliberately.

## Helper Scripts

- `scripts/probe_ripgrep.py` builds a temporary corpus and verifies real `rg` behavior such as ignore precedence, JSON output, multiline matching, and PCRE2 support.
- `scripts/validate.py` checks structure, frontmatter, references, required files, and Python syntax.
- `scripts/test_skill.py` runs validation, checks eval coverage, verifies cross-references, and executes the ripgrep probe suite.
