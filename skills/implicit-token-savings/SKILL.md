---
name: implicit-token-savings
description: "Force compact, low-noise tool selection for coding sessions by preferring terse filesystem, git, test, and container commands that surface only the needed signal. Use when an agent is exploring a repo, reading files, checking status, diffing changes, scanning history, running tests, or probing containers and wants to minimize context and token burn. Triggers on: token savings, compact commands, terse shell workflow, repo exploration, git status, git diff, git log, rg, tree, npm test, cargo test, pytest, go test, docker ps. Do NOT trigger for binary inspection, workflows where full human-facing output is the goal, or cases where the user explicitly wants whole-file dumps."
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

Bias every coding session toward the smallest command that answers the real question.

Prefer inventories, summaries, scoped searches, and path-selective test commands before full file dumps, wide diffs, or whole-repo test runs.

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
  - Review the staged summary before the commit
  - Push `HEAD` instead of spelling the branch when the remote is already known
  - Read `references/git.md`

- Test, lint, or container health for a specific stack
  - Start with the narrowest stack-native command that exists: `cargo test`, `npm test`, `ruff check`, `pytest`, `go test`, or `docker ps`
  - Read `references/runners.md`

- The preferred command is missing
  - Follow the fallback matrix
  - Read `references/patterns.md`

## Default Operating Rules

1. Inventory before contents. Ask "which path?" before "what does the whole file say?"
2. Scope before detail. Prefer `--files`, `--name-only`, `--stat`, and explicit paths before raw output.
3. Search before read. Use `rg` to identify the few files worth opening.
4. Summarize before hunk. Use `git diff --stat` or `git diff --name-only` before `git diff`.
5. Narrow test surfaces aggressively. Run the smallest path, package, test name, or pattern that can answer the question.
6. Prefer machine-readable output when another tool or script will consume it: `--json`, `--format '{{json .}}'`, `jq -r`.
7. Escalate in steps: terse, then structured, then full output.
8. If a preferred tool is absent, use the nearest cheaper equivalent rather than stalling.

## Quick Reference

| Need | Start here | Escalate only if needed | Why |
| --- | --- | --- | --- |
| Top-level repo inventory | `ls -1` | `ls -lah`, then `tree -L 2` | File names beat decorative output when you just need bearings |
| Directory shape | `tree -L 2 path/` | `tree -a -L 3 path/` | Depth caps keep structure readable |
| Candidate paths only | `rg --files path/` | `rg --files path/ \| rg 'pattern'` | Avoid opening file contents at all |
| Text or symbol search | `rg -n -F 'needle' path/` | `rg -n 'regex' path/` | Match first, read later |
| File excerpt | `sed -n '1,80p' file` | `head -n 120 file`, then full read | Pull only the needed slice |
| Working tree state | `git status --short --branch` | `git status` | Short form is enough for most decisions |
| Change scope | `git diff --stat` | `git diff --name-only`, then `git diff -- path` | Summaries first, hunks last |
| Recent history | `git log --oneline --decorate -n 15` | `git log --stat -- path` | Commit headlines answer many questions quickly |
| Stage and review | `git add -- path && git diff --cached --stat` | `git diff --cached -- path` | Review only what you are about to commit |
| Push current branch | `git push -u origin HEAD` | `git remote -v`, then explicit branch push | `HEAD` avoids branch-name lookup noise |
| Node test surface | `npm test -- --help` | `npm test -- <runner-args>` | Confirm how the project forwards args before widening |
| Rust test surface | `cargo test name -- --nocapture` | `cargo test package::module::name` | Target a single test before a suite |
| Python lint surface | `ruff check path/` | `ruff check path/ --fix` | Keep fixes explicit |
| Python test surface | `pytest -q tests/test_file.py -k expr` | `pytest -q tests/` | Start with a file or expression, not the whole suite |
| Go test surface | `go test ./pkg/... -run Pattern` | `go test ./...` | Package and `-run` filters cut noise |
| Container inventory | `docker ps --format '{{json .}}'` | `docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'` | Structured rows are easier to filter or summarize |

## Reading Guide

| Task | Read |
| --- | --- |
| Repo shape, search, and targeted file reads | `references/filesystem.md` |
| Compact git status, diff, history, staging, and push patterns | `references/git.md` |
| Narrow test, lint, and container commands | `references/runners.md` |
| Fallbacks, escalation ladders, and session choreography | `references/patterns.md` |
| Missing results, over-compression mistakes, and command traps | `references/gotchas.md` |

## Verified Environment

- Verified locally on April 19, 2026 in a Unix-like shell.
- Found during verification: `/bin/ls`, `tree 2.2.1`, `ripgrep 15.1.0`, `git 2.53.0`, `npm 11.7.0`, `docker 28.5.2`, and `jq 1.8.1`.
- Not on `PATH` during verification: `cargo`, `ruff`, `pytest`, and `go`.
- Re-run `python3 scripts/probe_implicit_token_savings.py --format pretty` to refresh availability and behavior on the current machine.

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
