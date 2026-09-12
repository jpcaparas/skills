# Workflow

Use this reference when you need the exact operating sequence for building a client report from git history.

## Preconditions

- The user has provided an exact start date in `YYYY-MM-DD`.
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

## 2. Refuse Ambiguous Dates

Do not translate relative phrases on the user's behalf.

If the request says any of these, stop and ask for an exact date:

- `this week`
- `recently`
- `a few days ago`
- `since the last deploy`
- `since launch`

Use this exact question:

```text
What exact start date should I use? Please reply in YYYY-MM-DD.
```

## 3. Gather the Commit Context

Use the helper script first because it gives you commit subjects, scopes, files, and top-level path counts in one pass:

```bash
python3 scripts/collect_git_changes.py --repo /path/to/repo --since 2026-04-01
```

Add `--until YYYY-MM-DD` when the user gives a bounded range.

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

Open `templates/client-report-template.md` and fill it in with client-safe language.

Before finalizing, check that the report:

- is grouped by feature, not by commit
- has no more than `2-3` bullets in each section
- avoids hashes, filenames, branch names, and internal tooling references
- uses plain Markdown that can be pasted directly into email or chat
