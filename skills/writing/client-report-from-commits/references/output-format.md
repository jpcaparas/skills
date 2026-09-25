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

Default to this shape when the user has not requested another form:

1. One-line intro naming the date range.
2. Short feature heading for each main accomplishment.
3. A few concise bullets per feature, with the count determined by distinct meaningful changes.

A short email paragraph, table, or single bullet can be enough. Do not force headings, pad to a minimum, or compress unrelated outcomes merely to fit a template.

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

- `Added a saved-address option to checkout.` (when the diff establishes it)
- `Added overdue invoices to the reporting view.` (when the diff establishes it)

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

If evidence supports the benefit, say it plainly. Do not imply deployment or measured impact from implementation alone.

If the benefit is not clear from the diff, state the changed capability or unfinished work rather than inventing a softer-sounding benefit. Phrases such as these still require a concrete basis:

- `advanced the work on`
- `improved the foundation for`
- `continued refining`
- `tightened the workflow around`

## Final Pass Checklist

- Length and grouping match the requested form and the substance of the changes.
- Every bullet is safe for a non-technical audience.
- Duplicate themes across commits have been merged into one section.
- The final report can be pasted directly into the requested destination.
