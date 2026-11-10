---
name: client-report-from-commits
description: "Turns git commits and diffs into a non-technical client update grouped by feature. Use for client updates, weekly progress reports, stakeholder recaps or git-history summaries. Not for release notes, changelogs or code review."
---

# Client report from commits

## Date range and repo

- Work in the current directory if it is a git repo, otherwise require an explicit repo path (use `git -C`). If neither is readable, ask for one.
- Resolve the range to exact `YYYY-MM-DD` dates and state them with any timezone assumption. Resolve unambiguous relative dates ("since yesterday") from a reliable clock without asking. Ask when the boundary is genuinely unclear ("recently", "this week" with no week-start convention, "since the last push/deploy" with no recorded event). Never infer a push or deployment date from commit timestamps.
- `python3 scripts/collect_git_changes.py --repo /path/to/repo --since YYYY-MM-DD [--until YYYY-MM-DD]` prints a JSON inventory of commits, Conventional Commit scopes, files and top-level path counts. It accepts only exact `YYYY-MM-DD` dates, so resolve relative phrases first. Plain `git log`/`git show` is fine when it is enough.

## Writing the report

- Group by feature, workflow or product area, never by commit, file, branch or engineer. Merge commits that are one accomplishment. Scopes and shared directories are the best grouping signals.
- Commit subjects are written for developers (`refactor worker queue`, `fix flaky spec`); read the diff before translating them into client language.
- Write for a non-technical client: no hashes, filenames, code terms, refactor jargon or internal tooling. Lead each bullet with the outcome, ideally one short sentence ("Added a saved-address option to checkout.").
- Claim only what the history supports. Commits do not prove deployment, adoption or business impact, so do not promise faster conversions or fewer tickets. Vague softeners ("improved the foundation for") still need a concrete basis. Mention housekeeping, dependency bumps or CI work only if it matters to the client, in one modest "Stability and foundations" section.
- Default output is copy-pastable Markdown: a one-line intro naming the range ("Here is a high-level update for work completed since 2026-04-01."), then short feature headings with as many bullets as there are distinct changes. No analysis notes or developer preamble. If there was nothing client-facing, say so plainly.
