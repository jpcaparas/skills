# Output Format

Use this reference when you are shaping the final client-facing update.

## Audience

Write for a non-technical client or stakeholder.

Assume the reader wants:

- what changed
- where progress happened
- why it matters at a high level

Assume the reader does not want:

- commit hashes
- filenames
- internal module names
- refactor details
- branch or pull request mechanics

## Structure

Use this shape:

1. One-line intro naming the date range.
2. Short feature heading for each main accomplishment.
3. `2-3` bullets max per feature section.

Recommended heading style:

- `## Checkout Experience`
- `## Reporting and Visibility`
- `## Admin Workflow`

## Bullet Rules

Each bullet should:

- start with the accomplishment, not the implementation detail
- stay to one short sentence whenever possible
- explain the result in plain language
- avoid overclaiming impact that the diff does not prove

Prefer:

- `Improved the checkout flow so customers can move through payment with less friction.`
- `Expanded reporting so the team can track progress and spot issues more quickly.`

Avoid:

- `Refactored payment handlers and renamed `src/billing/flow.ts`.`
- `Touched 14 files to clean up cron orchestration and CI jobs.`

## Grouping Rules

Group by feature or user-facing workflow, not by the number of commits.

Good main-accomplishment groups:

- onboarding
- checkout
- reporting
- content publishing
- admin controls

Weak groups:

- backend cleanup
- bug fixes
- miscellaneous changes
- commit-by-commit summaries

## Conservative Language

If the benefit is clear, say it plainly.

If the benefit is not clear from the diff, use modest language:

- `advanced the work on`
- `improved the foundation for`
- `continued refining`
- `tightened the workflow around`

## Final Pass Checklist

- Each section has `2-3` bullets max.
- Every bullet is safe for a non-technical audience.
- Duplicate themes across commits have been merged into one section.
- The final Markdown can be pasted directly into an email or chat message.
