# Session Checklist

Use the applicable checks when choosing sufficient, low-noise commands; this is not an execution sequence.

- Use known tool availability or a focused check. Run `python3 scripts/probe_implicit_token_savings.py --format pretty` only when a comprehensive probe helps.
- Inventory with `ls -1`, `tree -L 2`, or `rg --files` when paths or shape are unknown.
- Use `rg -n` for matching text; read a known relevant file or excerpt directly.
- Choose full-file context immediately when needed rather than forcing smaller reads first.
- Use `git status --short` or `git diff --stat` for state or scope, and a relevant diff for semantics.
- When committing is authorized, stage explicit paths and review all staged changes. Push only with separate authority for that external write.
- Choose focused tests for feedback and run all repository-required gates before handoff.
- Use structured output for containers or JSON when another tool will consume it; preserve errors and failure details in every format.
