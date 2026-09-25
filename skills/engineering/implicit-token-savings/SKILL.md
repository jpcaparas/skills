---
name: implicit-token-savings
description: "Selects sufficient, low-noise local shell commands for repository exploration, git inspection, tests, and container checks. Use when choosing command scope or output detail, especially for token savings or terse workflows; not for incidental tool mentions or requests for full output."
compatibility: "Requires: python3 and a Unix-like shell. Best with rg, tree, git, npm, docker, and jq; degrades cleanly when some tools are absent."
metadata:
  version: "1.0.0"
  short-description: "Prefer compact shell commands that reveal only the needed signal"
  openclaw:
    category: "development"
    subcategory: "workflow"
    requires:
      bins: [python3]
    tags: ["tokens", "shell", "git", "rg", "tests", "docker", "workflow"]
references:
  - filesystem
  - git
  - runners
  - patterns
  - gotchas
---

# implicit-token-savings

Choose the smallest sufficient local shell command for the real question.

Prefer compact output when it answers the question, especially when requested. Go directly to a known file, relevant diff, or full output when the task needs it; preliminary summaries are not prerequisites.

## Decision Tree

What do you need right now?

- Repo shape, top-level files, or candidate paths
  - Start with `ls -1`, `tree -L 2`, or `rg --files`
  - Read `references/filesystem.md`

- A specific symbol, literal, stack trace, or TODO
  - Start with `rg -n`
  - Read `references/filesystem.md`

- A file excerpt or line range
  - Prefer the harness's targeted read tool if one exists
  - Otherwise use `sed -n 'start,endp' file`, `head -n 80`, or `tail -n 80`
  - Read `references/filesystem.md`

- Working tree state, scope of change, or recent history
  - Start with `git status --short`, `git diff --stat`, `git diff --name-only`, or `git log --oneline`
  - Read `references/git.md`

- Staging, committing, or pushing
  - Stage only the intended paths
  - Review all staged changes before an authorized commit; use summaries for scope and hunks for semantics
  - Only when pushing is authorized, use `HEAD` if the intended remote and destination are known
  - Read `references/git.md`

- Test, lint, or container health for a specific stack
  - Start with the narrowest stack-native command that exists: `cargo test`, `npm test`, `ruff check`, `pytest`, `go test`, or `docker ps`
  - Read `references/runners.md`

- The preferred command is missing
  - Follow the fallback matrix
  - Read `references/patterns.md`

## Default Operating Rules

1. Use known context to choose a sufficient command directly. Inventory helps when paths are unknown, not when the target file is already named.
2. Keep scope explicit. Use `--files`, `--name-only`, or `--stat` for scope questions, and content output for semantic questions.
3. Use `rg` to locate unknown files or matching lines; read known relevant files without a search ceremony.
4. Use a path-specific `git diff` directly when reviewing behavior. Summaries help size or file-list questions but cannot establish semantics.
5. Use focused tests for local feedback, and run all repository-required validation gates before handoff. Narrow tests do not replace required full suites.
6. Prefer machine-readable output when another tool or script will consume it: `--json`, `--format '{{json .}}'`, `jq -r`.
7. Choose terse, structured, or full output to match the known need. Preserve errors, exit status, and failure details; never compress away evidence needed for a safe decision.
8. If a preferred tool is absent, use the nearest cheaper equivalent rather than stalling.

## Quick Reference

Choose a row for the question at hand; alternatives are not a required sequence.

| Need | Compact option | Alternative when useful | Why |
| --- | --- | --- | --- |
| Top-level repo inventory | `ls -1` | `ls -lah` or `tree -L 2` | File names beat decorative output when you just need bearings |
| Directory shape | `tree -L 2 path/` | `tree -a -L 3 path/` | Depth caps keep structure readable |
| Candidate paths only | `rg --files path/` | `rg --files path/ \| rg 'pattern'` | Avoid opening file contents at all |
| Text or symbol search | `rg -n -F 'needle' path/` | `rg -n 'regex' path/` | Choose literal or pattern semantics |
| File excerpt | `sed -n '1,80p' file` | Full read when whole-file context is needed | Pull enough context in one useful read |
| Working tree state | `git status --short --branch` | `git status` | Short form is enough for most decisions |
| Change scope or semantics | `git diff --stat` | `git diff --name-only` for paths; `git diff -- path` for semantics | Choose the detail the question requires |
| Recent history | `git log --oneline --decorate -n 15` | `git log --stat -- path` | Commit headlines answer many questions quickly |
| Stage and review | `git add -- path && git diff --cached --stat` | `git diff --cached -- path` | Review only what you are about to commit |
| Authorized push of current branch | `git push -u origin HEAD` | Inspect the destination if unknown | `HEAD` is shorthand, not push authorization |
| Node test surface | `npm test -- <runner-args>` | `npm test -- --help` if flags are unknown | Use the project's known runner contract |
| Rust test surface | `cargo test name -- --nocapture` | `cargo test package::module::name` | Choose a test filter for focused feedback |
| Python lint surface | `ruff check path/` | `ruff check path/ --fix` | Keep fixes explicit |
| Python test surface | `pytest -q tests/test_file.py -k expr` | `pytest -q tests/` | Choose focused feedback or suite coverage as needed |
| Go test surface | `go test ./pkg/... -run Pattern` | `go test ./...` | Package and `-run` filters cut noise |
| Container inventory | `docker ps --format '{{json .}}'` | `docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'` | Structured rows are easier to filter or summarize |

## Reading Guide

| Task | Read |
| --- | --- |
| Repo shape, search, and targeted file reads | `references/filesystem.md` |
| Compact git status, diff, history, staging, and push patterns | `references/git.md` |
| Narrow test, lint, and container commands | `references/runners.md` |
| Context-driven command choices and fallbacks | `references/patterns.md` |
| Missing results, over-compression mistakes, and command traps | `references/gotchas.md` |

## Gotchas

1. `rg` respects ignore rules. Missing results usually need `--hidden`, `-u`, or `--debug`, not a tool switch.
2. `tree` is for shape, not truth. Cap depth early or you will spend tokens on directory art.
3. `sed -n` is cheaper than `cat` when you need a slice, but repeated slicing can cost more than one full read once you know the exact short file you need.
4. `git diff --stat` hides semantics. Escalate to a path-specific diff before drawing conclusions about behavior.
5. `npm test` forwards extra runner flags only after `--`.
6. `docker ps` can succeed while the container you care about is unhealthy. Read `Status`, not just presence.
7. `git add .` is the opposite of token discipline when only one file matters. Stage explicit paths.

## Helper Scripts

- `scripts/probe_implicit_token_savings.py` detects available tools and verifies compact command behavior on temporary local fixtures.
- `scripts/validate.py` checks packaging, required files, and syntax.
- `scripts/test_skill.py` runs validation, eval coverage checks, cross-reference checks, and the probe suite.
- `templates/session-checklist.md` is a reusable checklist for starting a low-noise coding session.

## When Guidance Stops Helping

If a compact command fails or hides needed evidence, use fuller output and inspect installed help or official version-matched docs. Preserve failures and unknowns rather than optimizing them away. Propose a canonical skill update when an example is stale or saves less work than it adds, citing the tool/version and a reproducer. Do not silently edit installed copies or publish the proposal.
