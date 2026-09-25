# Compact Git Patterns

Choose summaries for scope and state, patches for semantics, and history for provenance.

## Choose The Needed View

- Working-tree state: `git status --short --branch`
- Change size or paths: `git diff --stat` or `git diff --name-only`
- Behavior changes in a known file: `git diff -- path/to/file`
- Staged scope or semantics: `git diff --cached --stat` or `git diff --cached -- path/to/file`
- Recent history: `git log --oneline --decorate -n 15`
- Path history with change size: `git log --stat -- path/to/file`
- A commit summary: `git show --stat --oneline <commit>`

These are alternatives, not a ladder. Read a full diff directly when the task requires the complete patch; prefer explicit paths when the relevant scope is known.

## Quick Reference

| Need | Compact option | Alternative when useful | Why |
| --- | --- | --- | --- |
| Current branch and file states | `git status --short --branch` | `git status` | Branch plus concise state codes answer most triage questions |
| How large the change is | `git diff --stat` | `git diff --name-only` | File counts and line totals are cheap signal |
| Which files changed | `git diff --name-only` | `git diff --name-status` | Names come before semantics |
| What changed in one file | `git diff -- path/to/file` | `git diff -U20 -- path/to/file` | Keep the scope path-specific |
| What is staged | `git diff --cached --stat` | `git diff --cached -- path/to/file` | Review the commit surface before the commit |
| Recent history | `git log --oneline --decorate -n 15` | `git log --stat -- path/to/file` | Headlines first, detail when needed |
| Last commit summary | `git show --stat --oneline HEAD` | `git show HEAD -- path/to/file` | Start with the commit envelope |

## Staging, Commit, and Push Flow

When committing is authorized, stage only intended changes and review their semantics:

```bash
git add -- path/to/file
git diff --cached -- path/to/file
git commit -m "fix(scope): concise summary"
```

Use `git diff --cached --stat` if a staged-size summary helps. Review all staged changes that would enter the commit, including any already present; never silently include unrelated work.

Pushing is a separate external write, not an implied next step after committing. Only when the user has authorized a push and the intended remote and destination are known:

```bash
git push -u origin HEAD
```

`HEAD` avoids a branch-name lookup; it does not choose or authorize a destination. Use an explicit refspec when the intended destination differs, and `-u` only when setting the upstream is intended.

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

## Detail Choices

- If `git diff --stat` says the change is trivial, inspect only the affected paths.
- If the summary suggests rename-heavy or generated-file churn, use `git diff --name-status` before opening hunks.
- If the user wants the exact patch or asks for code review, path-specific diffs are fine. The optimization goal is to avoid premature wide output, not to avoid diffing forever.

See `references/gotchas.md` for stage/push traps and `references/patterns.md` for fallback choices when a preferred git form is unavailable.
