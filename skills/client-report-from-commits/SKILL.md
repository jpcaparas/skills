---
name: client-report-from-commits
description: "Turn git commits and diffs since an exact start date into a copy-pastable, non-technical client report grouped by feature. Use when the user wants a client update, accomplishment summary, weekly progress note, stakeholder recap, or high-level status report based on git history. Trigger on: client report from commits, summarize git diff since a date, weekly update from git log, non-technical accomplishments, stakeholder-ready changelog. Do NOT trigger for technical release notes, code review, or any request where the date is still ambiguous."
---

# client-report-from-commits

Turn git history since an explicit date into a copy-pastable, non-technical client update grouped by feature.

## Decision Tree

What do you know already?

- Exact start date in `YYYY-MM-DD` and the current working directory is the target git repo: continue.
- Exact start date in `YYYY-MM-DD`, but the target repo is elsewhere: use the explicit repo path and continue.
- Relative or vague date such as "this week", "recently", "a few days ago", or "since the last push": stop and ask `What exact start date should I use? Please reply in YYYY-MM-DD.` Do not proceed until the user answers with an exact date.
- No readable git repo in the current working directory and no repo path was provided: stop and ask for a readable git repository path.
- The user wants engineering release notes, a developer changelog, or a code review: do not use this skill.

## Quick Reference

| Task | Action |
| --- | --- |
| Confirm the repo | Run `git rev-parse --show-toplevel` in the current directory, or `git -C /path/to/repo rev-parse --show-toplevel` when a repo path is provided. |
| Gather commit context | Run `python3 scripts/collect_git_changes.py --repo /path/to/repo --since YYYY-MM-DD`. |
| Inspect more detail | Read `references/workflow.md` and then inspect targeted commits with `git show <commit>`. |
| Shape the client update | Use `templates/client-report-template.md` and the language rules in `references/output-format.md`. |
| Handle edge cases | Read `references/gotchas.md`. |

## Operating Rules

1. Confirm the date before doing anything else. Exact means a real calendar date, not a relative phrase.
2. Confirm the repository context. If the current working directory is not a readable git repo, require an explicit repo path.
3. Collect the commit list and touched files first. Use `scripts/collect_git_changes.py` for a fast high-level pass, then inspect specific commits only when the summary is unclear.
4. Group the work by feature, workflow, or product area. Do not group by commit, file, branch, or engineer.
5. Write for a non-technical client. Remove hashes, filenames, code terms, refactor jargon, and internal tooling names unless they are truly client-facing.
6. Keep each main accomplishment to a heading plus `2-3` bullets max. Each bullet should be one short sentence.
7. Do not invent business impact. If the value is unclear, use conservative phrasing such as "improved the foundation for" or "advanced the work on".

## Recommended Workflow

1. Resolve the target repo.
2. Require an exact `YYYY-MM-DD` start date.
3. Run `python3 scripts/collect_git_changes.py --repo /path/to/repo --since YYYY-MM-DD` and review the JSON output.
4. Inspect a few representative commits or diffs when the feature grouping is not obvious.
5. Build a feature-based outline first, then write the client-safe bullets.
6. Paste the final answer in plain Markdown using `templates/client-report-template.md` as the shape.

## Report Contract

Use this exact standard:

- Start with a one-line intro such as `Here is a high-level update for work completed since 2026-04-01.`
- Break the report into feature sections with short audience-friendly headings.
- Keep each section to `2-3` bullets max.
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

1. Ambiguous dates are a hard stop. Do not translate "this week" or "a few days ago" yourself.
2. A long git log is not a client report. Condense by feature and omit low-signal internal churn when it is not useful to the client.
3. Technical commit subjects are often misleading for a non-technical audience. Inspect the diff or surrounding files before rewriting them as client-facing bullets.
4. Multiple commits may represent one accomplishment. Merge them into one feature section instead of repeating the same theme.
5. Infrastructure-only changes should not be exaggerated. If they matter, frame them as stability or foundation work and keep the wording modest.
