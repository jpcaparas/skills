---
name: implicit-token-savings
description: "Chooses the smallest sufficient shell command for repository exploration, git inspection, test and lint runs, and container checks. Use when picking command scope or output detail. Not for incidental tool mentions or requests for full output."
compatibility: "Best with rg, git, jq, and a Unix-like shell; degrades to the nearest cheaper equivalent when a tool is missing."
---

# implicit-token-savings

Match output size to the question, not to a ritual. When the target file is already named, read it; when the user asks for full output, give it. Summaries are never a prerequisite, and a compact command that hides evidence is a false saving.

## Choosing detail

- Unknown paths: `rg --files path/`, or `tree -L 2`. Cap depth; `tree` shows shape, not truth.
- Unknown location of a symbol or literal: `rg -n -F 'needle' path/` (`-F` for literals). Known relevant file: read it directly. A short, central file is cheaper in one full read than in repeated `sed -n` slices.
- Scope questions use `git status --short --branch`, `git diff --stat`, `git diff --name-only`, `git log --oneline -n 15`. Semantic questions need the content: `git diff -- path`, `git diff --cached -- path`. `--stat` compresses volume, not meaning.
- Tests and lint: the narrowest stack-native command for local feedback (`pytest -q file -k expr`, `go test ./pkg/... -run X`, `cargo test name`, `ruff check path/`). Narrow runs never replace the full gates the repository requires before handoff, and failure output, exit status and error details are never trimmed away.
- Output another tool will consume: `--json`, `docker ps --format '{{json .}}'`, `jq -r`.
- A preferred tool is missing: use the nearest cheaper equivalent rather than stalling.

## Gotchas

- `rg` obeys ignore files; an expected match that does not appear usually needs `--hidden`, `-u` or `--debug`, or a different root, not another tool.
- `npm test` forwards runner flags only after `--`: `npm test -- --runInBand`.
- `docker ps` listing a container does not mean it is healthy; read `Status`.
- Stage explicit paths (`git add -- path`), never `git add .`, then check `git diff --cached --stat` before an authorised commit. `git push -u origin HEAD` is shorthand for the destination, not authorization to push; it fails with no `origin` or a detached HEAD, so check `git remote -v` and `git branch --show-current`.

`scripts/probe_implicit_token_savings.py` (optional, `--format json`) reports which of these tools exist and exercises the compact commands on temporary local fixtures.
