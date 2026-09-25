# Compression Patterns and Fallbacks

Treat command selection like a compression problem: keep the highest-value signal and discard decorative noise until detail is genuinely required.

## Optional Environment Probe

When a comprehensive availability and behavior check would be useful, run:

```bash
python3 scripts/probe_implicit_token_savings.py --format pretty
```

That gives you:

- Which preferred tools exist
- Which behaviors were verified on this machine
- Which runners are absent and should not be assumed

It is not a session prerequisite. Use existing environment evidence or a targeted availability check when only one command matters.

## High-Value Heuristics

1. Identify the immediate question: paths, matches, state, history, test surface, or container state.
2. Choose the smallest command that answers only that question.
3. Restrict by path, package, file, filter, or test name before widening.
4. Use machine-readable output when another tool or script will consume the result.
5. Parallelize independent read-only probes when the harness supports it, but keep each probe narrow.
6. Go directly to detailed output when it is known to be needed. Otherwise expand when the compact result leaves a concrete gap, retaining errors and failure context.

## Fallback Matrix

| Preferred | If missing | Last resort | Notes |
| --- | --- | --- | --- |
| `tree -L 2` | `ls -R` on a narrow path | `find path -maxdepth 2` | Keep depth capped no matter which tool you use |
| `rg --files` | `find path -type f` | `git ls-files` in repos | Prefer path lists over content search |
| `rg -n` | `grep -R -n` | manual file reads | Literal search is still cheaper than blind opens |
| Targeted harness read | `sed -n` / `head` / `tail` | `cat` | A full read can also be the first choice when whole-file context is needed |
| `git status --short` | `git status` | none | Short form is a preference, not a separate capability |
| `git diff --stat` | `git diff --name-only` | `git diff` | Choose summaries for scope, hunks for semantics |
| `git log --oneline` | `git log --decorate --max-count=15` | `git log` | Stay headline-first |
| `docker ps --format '{{json .}}'` | `docker ps --format '{{.Names}}\t{{.Status}}'` | `docker ps` | Structured rows are easier to reuse |
| `jq -r` | language-native JSON parser | raw JSON | Use the cheapest parser already present |

## Context-Driven Choices

### Filesystem

- `ls -1` or `tree -L 2` for unfamiliar repository shape.
- `rg --files` for unknown paths; `rg -n` for text matches in a known scope.
- `sed -n` for a known excerpt, or a full-file read for a known file whose whole context matters.

### Git

- `git status --short` for state; `git diff --stat` or `--name-only` for scope.
- `git diff -- path` for the semantics of a known change; use `--cached` for staged changes.
- Full diff or `git show` when reviewing the complete patch or a commit.

### Tests

- Check availability only if the runner is unknown.
- Choose a file, package, test name, or suite that answers the question.
- Run full repository-required gates before handoff even when focused tests pass; these choices do not waive validation policy.

### Containers

- Filter `docker ps` to the known service and select text or structured output for its consumer.
- Inspect details directly when health, configuration, or another known question needs them.

## When to Stop Optimizing

Do not force compression when:

- The user explicitly wants the literal output
- A short summary hides the semantic detail needed for a safe decision
- The file is already tiny and a single full read is cheaper than multiple excerpts
- The task is a real code review and patch semantics matter

## Reusable Checklist

If you want a copyable checklist for a session or prompt, use `templates/session-checklist.md`.

See `references/gotchas.md` for failure modes that look like tooling issues but are usually scoping mistakes.
