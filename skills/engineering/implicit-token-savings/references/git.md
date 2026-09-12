# Compact Git Patterns

Use git as a summary engine first and a patch viewer second.

## The Git Compression Ladder

1. `git status --short --branch`
2. `git diff --stat`
3. `git diff --name-only`
4. `git diff -- path/to/file`
5. `git diff --cached --stat`
6. `git diff --cached -- path/to/file`
7. `git log --oneline --decorate -n 15`
8. `git log --stat -- path/to/file`
9. `git show --stat --oneline <commit>`

Do not jump to a full unscoped diff unless the summary still leaves a real ambiguity.

## Quick Reference

| Need | Preferred command | Escalate to | Why |
| --- | --- | --- | --- |
| Current branch and file states | `git status --short --branch` | `git status` | Branch plus concise state codes answer most triage questions |
| How large the change is | `git diff --stat` | `git diff --name-only` | File counts and line totals are cheap signal |
| Which files changed | `git diff --name-only` | `git diff --name-status` | Names come before semantics |
| What changed in one file | `git diff -- path/to/file` | `git diff -U20 -- path/to/file` | Keep the scope path-specific |
| What is staged | `git diff --cached --stat` | `git diff --cached -- path/to/file` | Review the commit surface before the commit |
| Recent history | `git log --oneline --decorate -n 15` | `git log --stat -- path/to/file` | Headlines first, detail when needed |
| Last commit summary | `git show --stat --oneline HEAD` | `git show HEAD -- path/to/file` | Start with the commit envelope |

## Staging, Commit, and Push Flow

Use the smallest safe commit workflow:

```bash
git add -- path/to/file
git diff --cached --stat
git diff --cached -- path/to/file
git commit -m "fix(scope): concise summary"
git push -u origin HEAD
```

Why this order:

- `git add -- path` stages only the intended surface
- `git diff --cached --stat` is the cheapest sanity check before commit
- `git diff --cached -- path` is the hunk-level review only for the file that matters
- `git push -u origin HEAD` avoids branch-name lookup noise when the remote exists

## Narrow History Patterns

### See recent history for one path

```bash
git log --oneline -- path/to/file
git log --stat -- path/to/file
```

### Follow a path through renames when the default view is too shallow

```bash
git log --follow --oneline -- path/to/file
```

### Summarize one commit without opening the whole patch

```bash
git show --stat --oneline <commit>
```

## Verified Local Behavior

The probe suite in `scripts/probe_implicit_token_savings.py` creates a temporary repository, stages a file, commits it, and pushes `HEAD` to a local bare remote. That verifies the compact add, commit, and push flow without touching any real repository.

## Escalation Rules

- If `git diff --stat` says the change is trivial, inspect only the affected paths.
- If the summary suggests rename-heavy or generated-file churn, use `git diff --name-status` before opening hunks.
- If the user wants the exact patch or asks for code review, path-specific diffs are fine. The optimization goal is to avoid premature wide output, not to avoid diffing forever.

See `references/gotchas.md` for stage/push traps and `references/patterns.md` for fallback choices when a preferred git form is unavailable.
