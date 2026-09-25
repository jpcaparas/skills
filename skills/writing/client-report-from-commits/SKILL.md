---
name: client-report-from-commits
description: "Turn git commits and diffs into a non-technical client report grouped by feature. Use for client updates, weekly progress, stakeholder recaps, or high-level git-history summaries; resolve the date range from reliable context or ask when ambiguous."
---

# client-report-from-commits

Turn git history for a resolved date range into a copy-pastable, non-technical client update grouped by feature.

## Decision Tree

What do you know already?

- Exact start date in `YYYY-MM-DD` and the current working directory is the target git repo: continue.
- Exact start date in `YYYY-MM-DD`, but the target repo is elsewhere: use the explicit repo path and continue.
- Unambiguous relative date with a reliable clock, timezone, and relevant context: resolve it and state the exact `YYYY-MM-DD` boundary and timezone before collecting history. No redundant confirmation is needed.
- Genuinely ambiguous range such as "recently", an unspecified week boundary, or "since the last push" without a known event boundary: ask a focused question. Do not guess a push or deployment date from commit timestamps.
- No readable git repo in the current working directory and no repo path was provided: stop and ask for a readable git repository path.
- The user wants engineering release notes, a developer changelog, or a code review: do not use this skill.

## Quick Reference

| Task | Action |
| --- | --- |
| Confirm the repo | Run `git rev-parse --show-toplevel` in the current directory, or `git -C /path/to/repo rev-parse --show-toplevel` when a repo path is provided. |
| Gather commit context | Use direct git history and diffs, or run `python3 scripts/collect_git_changes.py --repo /path/to/repo --since YYYY-MM-DD` for a structured inventory. |
| Inspect more detail | Read `references/workflow.md` and then inspect targeted commits with `git show <commit>`. |
| Shape the client update | Follow the requested format; `templates/client-report-template.md` is an optional starting point and `references/output-format.md` offers writing guidance. |
| Handle edge cases | Read `references/gotchas.md`. |

## Operating Rules

1. Establish real calendar boundaries from the request or reliable context. The helper accepts only `YYYY-MM-DD`; resolve relative language before calling it, without changing its strict parser.
2. Confirm the repository context. If the current working directory is not a readable git repo, require an explicit repo path.
3. Ground the report in the relevant history and diffs. Use `scripts/collect_git_changes.py` when its inventory helps; do not recollect evidence already sufficient for the task.
4. Group the work by feature, workflow, or product area. Do not group by commit, file, branch, or engineer.
5. Write for a non-technical client. Remove hashes, filenames, code terms, refactor jargon, and internal tooling names unless they are truly client-facing.
6. Keep the report concise in the requested form. Choose headings, paragraphs, or bullet counts from the meaning, not a quota.
7. State only supported changes. Commits do not prove deployment, adoption, or business impact; modest-sounding claims also need evidence.

## Recommended Workflow

1. Resolve the target repo.
2. Resolve and state the exact `YYYY-MM-DD` boundaries and any material timezone assumption.
3. Collect history directly or use `python3 scripts/collect_git_changes.py --repo /path/to/repo --since YYYY-MM-DD` and review the JSON output.
4. Inspect a few representative commits or diffs when the feature grouping is not obvious.
5. Build a feature-based outline first, then write the client-safe bullets.
6. Deliver the report in the requested form; default to copy-pastable Markdown.

## Report Contract

Use these defaults unless the user requests another form:

- Start with a one-line intro such as `Here is a high-level update for work completed since 2026-04-01.`
- Break the report into feature sections with short audience-friendly headings.
- Use only as many bullets or sentences as needed to distinguish meaningful changes; do not pad or omit evidence to meet a count.
- Make every bullet outcome-first and non-technical.
- Keep the output copy-pastable. Do not wrap it in analysis notes or a developer preamble.
- If there were no meaningful client-facing changes in the requested window, say so plainly instead of padding the report.

## Reading Guide

| Need | Read |
| --- | --- |
| Repo checks, command flow, and git collection steps | `references/workflow.md` |
| Tone, grouping, and bullet-writing rules | `references/output-format.md` |
| Failure modes and what to avoid | `references/gotchas.md` |
| Blank client-ready structure | `templates/client-report-template.md` |

## Gotchas

1. Resolve relative dates only when the clock, timezone, and range meaning are reliable. Ask when a missing boundary could change the report.
2. A long git log is not a client report. Condense by feature and omit low-signal internal churn when it is not useful to the client.
3. Technical commit subjects are often misleading for a non-technical audience. Inspect the diff or surrounding files before rewriting them as client-facing bullets.
4. Multiple commits may represent one accomplishment. Merge them into one feature section instead of repeating the same theme.
5. Infrastructure-only changes should not be exaggerated. If they matter, frame them as stability or foundation work and keep the wording modest.

## When guidance is insufficient

If collection guidance is stale or conflicts with the repository, use repository history, diffs, configuration, and current official Git documentation to resolve the relevant behavior. Use verified commands within the task's read-only scope; disclose inaccessible or incomplete history. Propose a canonical skill correction with the source and a reproducing git example or check, rather than silently editing an installed copy. Routine reports do not require browsing.
