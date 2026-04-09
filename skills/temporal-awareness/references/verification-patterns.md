# Verification Patterns

Read this file when the prompt includes relative dates, volatile facts, or any request for "latest" or "current" information.

## Pattern 1: `latest`, `current`, `recent`, `now`

1. Capture the local clock with `scripts/capture_temporal_context.py`.
2. Treat the requested fact as untrusted until verified live.
3. Prefer authoritative primary sources:
   - official vendor docs for models, SDKs, and product availability
   - government sites for laws, rules, and elections
   - exchange or finance providers for prices
   - league or organizer sources for schedules and standings
4. State the exact date you are using in the answer.

## Pattern 2: `today`, `yesterday`, `tomorrow`, `this week`

1. Capture the timezone and local date first.
2. Convert the relative phrase into an absolute date or date range.
3. If the user's timezone is ambiguous, either ask or clearly state the timezone you assumed.
4. If the task also depends on live external facts, verify those separately.

Example answer shape:

```text
Using Pacific/Auckland time, "today" is 2026-04-09 and "yesterday" is 2026-04-08.
```

## Pattern 3: Timezone Comparison

Use the extra-zone support in `scripts/capture_temporal_context.py` instead of doing mental math.

```bash
python3 scripts/capture_temporal_context.py \
  --format markdown \
  --extra-zone America/New_York \
  --extra-zone Europe/London
```

Use IANA zone names such as `America/New_York`, not raw offsets, because DST changes make offsets drift.

## Pattern 4: Product and Model Freshness

Treat these as volatile unless just verified:

- model names and families
- model availability by plan or tier
- context windows and pricing
- API versions, rate limits, and retirement timelines
- release channels and rollout status

Do not answer from memory when the prompt uses words like `latest`, `best`, `current`, or `available now`.

## Pattern 5: Answer Format

When the user seems date-confused or the date boundary matters, answer in this order:

1. state the timezone
2. state the absolute date or time
3. state whether live verification was used
4. answer the actual question

## Pattern 6: Source Hierarchy

Use the lowest-latency accurate source that matches the claim:

1. system clock for local date/time/timezone
2. official first-party docs for model/product claims
3. official organization sources for schedules, laws, and policies
4. reputable market/weather feeds for rolling numerical data

## Cross-References

- Read `references/recency-triage.md` to classify the prompt first.
- Read `references/gotchas.md` for failure cases that look current but are actually stale-memory regressions.
