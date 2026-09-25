# Long Horizon

Read this file when a session may run for hours, cross date boundaries, or revisit rolling external data multiple times.

## Refresh Triggers

Reassess whether the anchor is still sufficient when any of these happen:

1. The session crosses midnight in the user's relevant timezone.
2. More than a few hours pass and the answer depends on `today`, `this week`, or a rolling window.
3. The user switches geography or timezone context.
4. The task revisits live external data such as prices, weather, releases, or schedules.
5. DST changes may have occurred between checks.

## Refresh Procedure

1. Reuse a freshly supplied reliable session clock if it resolves the question. Otherwise rerun `python3 scripts/capture_temporal_context.py --format markdown`, adding the user's IANA zone when needed. Capture for relevant day/DST boundary math rather than relying on an old offset.
2. Assess the active claim again. The optional `scripts/recency_guard.py` can assist, but a changed prompt does not mandate running it.
3. Re-verify rolling external claims when the earlier evidence is no longer fresh enough. This does not always require another clock capture.
4. Restate the new absolute date in the answer if the boundary matters.

## Multi-Step Workflows

For long-running investigations or recurring tasks:

- store the captured local and UTC timestamps alongside notes
- record the timezone used for each relative-date interpretation
- annotate external facts with the verification time and source
- check anchor and source freshness before finalizing; refresh only evidence the final answer needs

## Anti-Patterns

- Reusing a morning timestamp for an answer sent after midnight
- Carrying a timezone assumption from one user locale into another
- Treating a previously verified stock price, model availability, or schedule as still current without checking again

## Cross-References

- Read `references/bootstrap.md` for the base session-start workflow.
- Read `references/verification-patterns.md` for how to restate refreshed dates cleanly.
