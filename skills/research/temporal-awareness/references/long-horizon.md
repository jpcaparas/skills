# Long Horizon

Read this file when a session may run for hours, cross date boundaries, or revisit rolling external data multiple times.

## Refresh Triggers

Refresh the temporal anchor when any of these happen:

1. The session crosses local midnight.
2. More than a few hours pass and the answer depends on `today`, `this week`, or a rolling window.
3. The user switches geography or timezone context.
4. The task revisits live external data such as prices, weather, releases, or schedules.
5. DST changes may have occurred between checks.

## Refresh Procedure

1. Rerun `python3 scripts/capture_temporal_context.py --format markdown`.
2. Re-run `python3 scripts/recency_guard.py --prompt "..." --format markdown` if the active question changed.
3. Re-verify live external claims instead of assuming an earlier source is still current.
4. Restate the new absolute date in the answer if the boundary matters.

## Multi-Step Workflows

For long-running investigations or recurring tasks:

- store the captured local and UTC timestamps alongside notes
- record the timezone used for each relative-date interpretation
- annotate external facts with the verification time and source
- rerun the capture and verification flow before finalizing

## Anti-Patterns

- Reusing a morning timestamp for an answer sent after midnight
- Carrying a timezone assumption from one user locale into another
- Treating a previously verified stock price, model availability, or schedule as still current without checking again

## Cross-References

- Read `references/bootstrap.md` for the base session-start workflow.
- Read `references/verification-patterns.md` for how to restate refreshed dates cleanly.
