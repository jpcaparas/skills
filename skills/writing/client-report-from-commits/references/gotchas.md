# Gotchas

Use this reference when the git history or the request is messy.

## 1. Ambiguous Time Windows

Symptom: the user says `this week`, `recently`, `the last few days`, or another relative range.

Cause: relative dates are subjective and easy to misread.

Fix: stop immediately and ask `What exact start date should I use? Please reply in YYYY-MM-DD.`

## 2. Not Actually in a Git Repo

Symptom: `git rev-parse --show-toplevel` fails.

Cause: the current working directory is not the project root, or the user pointed to a non-repo path.

Fix: require a readable repo path and use `git -C /path/to/repo ...` for every follow-up command.

## 3. Commit Subjects Are Too Technical

Symptom: commit titles say things like `refactor worker queue`, `rename env vars`, or `fix flaky spec`.

Cause: developer-oriented subjects rarely explain client value on their own.

Fix: inspect the changed files or the surrounding commits before translating the work into client language.

## 4. One Feature Spread Across Many Commits

Symptom: several commits touch the same workflow or directory with slightly different messages.

Cause: the implementation happened incrementally.

Fix: merge them into one accomplishment section and summarize the outcome once.

## 5. Internal Work With No Safe Client Framing

Symptom: the range mostly contains housekeeping, dependency bumps, CI edits, or purely internal refactors.

Cause: not every code change is useful in a client update.

Fix: either omit it or keep it to one modest section such as `## Stability and Foundations` with restrained wording.

## 6. Overclaiming Value

Symptom: the report starts promising faster conversions, fewer support tickets, or higher reliability without evidence.

Cause: the rewrite added business outcomes the diff does not establish.

Fix: keep the wording high-level and factual. State what changed, not speculative results.
