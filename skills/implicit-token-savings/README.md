# implicit-token-savings

Production skill for forcing compact, high-signal command selection during coding sessions.

## What It Covers

- Preferring terse repo inventory commands over noisy directory dumps
- Preferring targeted file reads over blind `cat` habits
- Compressing git status, diff, history, stage, commit, and push workflows
- Narrowing stack-native test and lint commands before running wide suites
- Using structured container listings when Docker is available
- Detecting which preferred tools exist on the current machine before leaning on them

## Key Files

- `SKILL.md` - authoritative instructions
- `references/filesystem.md` - repo inventory, search, and targeted read patterns
- `references/git.md` - compact git workflows
- `references/runners.md` - narrow test, lint, and container commands
- `references/patterns.md` - fallback matrix and escalation rules
- `references/gotchas.md` - high-value pitfalls
- `scripts/probe_implicit_token_savings.py` - repeatable local verification suite
