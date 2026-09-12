# Compression Patterns and Fallbacks

Treat command selection like a compression problem: keep the highest-value signal and discard decorative noise until detail is genuinely required.

## Session Opener

When the environment is unknown, start here:

```bash
python3 scripts/probe_implicit_token_savings.py --format pretty
```

That gives you:

- Which preferred tools exist
- Which behaviors were verified on this machine
- Which runners are absent and should not be assumed

## High-Value Heuristics

1. Ask a one-line question first: paths, matches, state, history, test surface, or container state.
2. Choose the smallest command that answers only that question.
3. Restrict by path, package, file, filter, or test name before widening.
4. Use machine-readable output when another tool or script will consume the result.
5. Parallelize independent read-only probes when the harness supports it, but keep each probe narrow.
6. Escalate only after the current output fails to answer the question.

## Fallback Matrix

| Preferred | If missing | Last resort | Notes |
| --- | --- | --- | --- |
| `tree -L 2` | `ls -R` on a narrow path | `find path -maxdepth 2` | Keep depth capped no matter which tool you use |
| `rg --files` | `find path -type f` | `git ls-files` in repos | Prefer path lists over content search |
| `rg -n` | `grep -R -n` | manual file reads | Literal search is still cheaper than blind opens |
| Targeted harness read | `sed -n` / `head` / `tail` | `cat` | Full reads are acceptable when the file is short and clearly relevant |
| `git status --short` | `git status` | none | Short form is a preference, not a separate capability |
| `git diff --stat` | `git diff --name-only` | `git diff` | Summary before hunks |
| `git log --oneline` | `git log --decorate --max-count=15` | `git log` | Stay headline-first |
| `docker ps --format '{{json .}}'` | `docker ps --format '{{.Names}}\t{{.Status}}'` | `docker ps` | Structured rows are easier to reuse |
| `jq -r` | language-native JSON parser | raw JSON | Use the cheapest parser already present |

## Escalation Ladders

### Filesystem

1. `ls -1`
2. `tree -L 2`
3. `rg --files`
4. `rg -n`
5. `sed -n`
6. full-file read

### Git

1. `git status --short`
2. `git diff --stat`
3. `git diff --name-only`
4. `git diff -- path`
5. staged diff
6. full diff or `git show`

### Tests

1. availability check
2. one file, package, or test name
3. one suite
4. full suite

### Containers

1. filtered `docker ps`
2. structured `docker ps`
3. wider container inspection

## When to Stop Optimizing

Do not force compression when:

- The user explicitly wants the literal output
- A short summary hides the semantic detail needed for a safe decision
- The file is already tiny and a single full read is cheaper than multiple excerpts
- The task is a real code review and patch semantics matter

## Reusable Checklist

If you want a copyable checklist for a session or prompt, use `templates/session-checklist.md`.

See `references/gotchas.md` for failure modes that look like tooling issues but are usually scoping mistakes.
