# Session Checklist

Use this checklist when you want a repeatable low-noise workflow.

1. Run `python3 scripts/probe_implicit_token_savings.py --format pretty` if tool availability is unknown.
2. Inventory the repo with `ls -1`, `tree -L 2`, or `rg --files` before opening files.
3. Search with `rg -n` before reading.
4. Read only the slice you need with the harness read tool or `sed -n`.
5. Inspect change scope with `git status --short` and `git diff --stat` before full diffs.
6. Stage explicit paths and review staged scope before `git commit`.
7. Choose the narrowest stack-native test or lint command that exists.
8. Use structured output for containers or JSON when another tool will consume the result.
