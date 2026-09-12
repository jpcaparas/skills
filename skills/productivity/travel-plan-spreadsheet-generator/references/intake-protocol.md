# Intake Protocol

Use one consolidated intake pass or none at all.

## Core Rule

- If the user's message and attachments already provide enough information to build a materially correct workbook, do not ask more questions.
- If essential information is missing, ask exactly one clarification batch.
- Do not drip-feed questions during the build.

## Intake Sequence

1. Read the prompt, pasted notes, PDFs, screenshots, emails, and booking snippets.
2. Extract everything you can before asking the user anything.
3. Separate missing facts into:
   - blockers: without these, the workbook would be materially wrong
   - non-blockers: you can proceed with assumptions and visible flags
4. Ask one intake batch only when blockers remain.

## Required Grouping

Use this structure exactly:

```text
Required to proceed
- ...

Useful but optional
- ...

Documents or screenshots that would improve accuracy
- ...
```

## Intake Checklist

Cover these only when still missing and relevant:

- trip name or primary destination
- trip start and end dates
- departure date and final home arrival date
- cities or bases, and whether the trip is single-city or multi-city
- travellers and their roles
- passport nationality for each traveller when immigration or transit matters
- outbound and return flights
- transit airports or countries
- accommodation details
- fixed bookings and ticketed attractions
- fixed work, conference, family, or school commitments
- budget or price sensitivity
- pace preference
- mobility or accessibility constraints
- dietary constraints when meal planning matters
- shopping goals and who requested them
- whether the group mostly stays together or often splits
- whether to include a pre-departure day and a post-arrival recovery day
- whether official prep tasks should include visas, insurance, vaccines, medicine checks, eSIM, check-in windows, and customs or immigration setup
- preferred output filename if the user gave one

## What Counts as a Blocker

Treat these as blockers when they are missing or contradictory:

- no usable trip dates
- no usable destination or base
- no way to determine the traveller set when booking coverage depends on it
- a route or commitment conflict that would make the daily plan nonsense
- a missing departure or return boundary when the planner window would otherwise be fabricated

## What Does Not Need to Block the Build

Proceed with assumptions and flags when the user is missing:

- exact shopping budgets
- final restaurant choices
- whether a flexible day should lean shopping-heavy or sightseeing-heavy
- exact attraction coverage for the full group when the workbook can carry split-plan fallbacks
- exact prep-task ownership for every non-critical task

## Wording Rules

- Keep the blocker batch practical and short.
- State what you already inferred from the files so the user can correct you efficiently.
- Ask for missing facts once, then move into trip-model creation.
