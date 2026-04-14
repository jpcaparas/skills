# client-report-from-commits

Production skill for turning git history since an exact date into a copy-pastable client update grouped by feature.

## What It Covers

- Exact-date intake with a mandatory stop on ambiguous dates
- Git repository detection in the current directory or via an explicit path
- Deterministic commit collection through `scripts/collect_git_changes.py`
- Non-technical, feature-based accomplishment summaries for clients and stakeholders

## Key Files

- `SKILL.md` - authoritative instructions
- `references/workflow.md` - repo checks and git collection flow
- `references/output-format.md` - tone and structure rules for the client update
- `references/gotchas.md` - failure modes and rewrite traps
- `templates/client-report-template.md` - blank copy-pastable report shape
- `scripts/collect_git_changes.py` - helper for gathering commit context
