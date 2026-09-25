# Workflow

Use this reference when you need the exact operating sequence for building a client report from git history.

## Preconditions

- The start date is explicit or unambiguously resolved from reliable clock, timezone, and context, then stated in `YYYY-MM-DD`.
- The current working directory is a readable git repository, or the user has provided a readable repo path.
- The goal is a non-technical client update, not release notes for engineers.

## 1. Resolve the Repository

Prefer the current working directory when it is already a git repo:

```bash
git rev-parse --show-toplevel
```

When the user points you to another repo, stay explicit:

```bash
git -C /path/to/repo rev-parse --show-toplevel
```

If either command fails, stop and ask for a readable git repository path.

## 2. Resolve the Date Range

Resolve unambiguous relative language before invoking the helper. For example, with a trusted clock of 2026-09-25 in UTC, "since yesterday" means a start date of `2026-09-24` in UTC. State the resolved date and timezone; no confirmation is needed when the meaning is settled.

Ask a focused question only when the boundary remains unclear:

- `this week` without a known week-start convention
- `recently`
- `a few days ago`
- `since the last deploy` or `since launch` without a verified event boundary
- `since the last push` when the push boundary is not recorded

One possible question is:

```text
What exact start date should I use? Please reply in YYYY-MM-DD.
```

## 3. Gather the Commit Context

Use direct git evidence when sufficient. The optional helper gives commit subjects, scopes, files, and top-level path counts in one pass:

```bash
python3 scripts/collect_git_changes.py --repo /path/to/repo --since 2026-04-01
```

Add `--until YYYY-MM-DD` for a bounded range. The helper's strict parser requires real `YYYY-MM-DD` dates; it does not interpret relative phrases. Check boundary and timezone semantics for the collection method used so the stated range matches the actual query.

The helper output is best for:

- counting the commits in scope
- spotting repeated scopes such as `checkout` or `billing`
- seeing which top-level paths dominate the work
- deciding which commits deserve a deeper read

## 4. Inspect Only What You Need

When the helper output is too vague, inspect a few targeted commits:

```bash
git -C /path/to/repo log --since="2026-04-01 00:00:00" --date=short --reverse --stat --oneline
git -C /path/to/repo show <commit-hash>
```

Use these deeper checks sparingly. The goal is a clear client summary, not a full forensic audit.

## 5. Group the Work by Feature

Use the strongest grouping signal you can find:

1. Conventional Commit scopes such as `feat(checkout): ...`
2. Repeated directories or product areas in the changed files
3. Commit subjects that describe one customer-facing thread
4. Shared issue or ticket language in several commits

Merge multiple commits into a single accomplishment when they are part of one feature or workflow.

## 6. Write the Report

Follow the requested form with client-safe language. Use `templates/client-report-template.md` only when its sectioned Markdown shape is useful.

Before finalizing, check that the report:

- is grouped by feature, not by commit
- uses a concise number of sentences or bullets based on meaningful changes, not a fixed quota
- avoids hashes, filenames, branch names, and internal tooling references
- uses the requested format, defaulting to copy-pastable Markdown
- does not imply deployment, adoption, or impact from commits alone
