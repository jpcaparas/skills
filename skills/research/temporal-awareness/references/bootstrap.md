# Bootstrap

Read this file when you need to load the real date, time, and timezone into the session before answering.

## Session-Start Protocol

1. Check the existing session anchor and known user timezone. Reuse them when reliable and fresh enough for the question. If missing, stale, or boundary math matters, capture the clock; add the user's IANA zone when it differs from the host:

```bash
python3 scripts/capture_temporal_context.py --format markdown --extra-zone America/New_York
```

2. Assess whether the requested claim is volatile. The optional guard can flag risks, but its keyword matches are advisory:

```bash
python3 scripts/recency_guard.py --prompt "What is the latest OpenAI model for coding?" --format markdown
```

3. Verify genuinely changing external claims against current authoritative sources. A guard label neither proves volatility nor excuses skipping verification of a volatile fact.
4. Interpret relative dates in the user's timezone. Restate absolute dates and the zone when ambiguity or boundaries matter, without dumping unrelated clock metadata.
5. Reassess anchor freshness after long pauses or relevant boundaries. Read `references/long-horizon.md` when refresh decisions are unclear.

## What the Capture Script Returns

| Field | Meaning |
| --- | --- |
| `local.iso` | Local timestamp with offset |
| `utc.iso` | UTC timestamp for cross-checking |
| `timezone.primary` | Best-effort local timezone identifier |
| `timezone.abbreviation` | Current timezone abbreviation, such as `NZST` |
| `timezone.utc_offset` | Offset from UTC in `±HH:MM` form |
| `locale` | Locale hints from the environment |
| `system` | Host, platform, and Python version used to generate the anchor |
| `session_directives` | General reminders; apply the canonical skill's scope and freshness rules |

## Useful Variants

Compare multiple zones:

```bash
python3 scripts/capture_temporal_context.py \
  --format markdown \
  --extra-zone America/New_York \
  --extra-zone Europe/London
```

Get machine-readable output:

```bash
python3 scripts/capture_temporal_context.py --format json
```

## Use the Right Source of Truth

- Use a reliable session/system clock for the current instant. The host's local zone is not evidence of the user's zone; known user timezone takes precedence for user-relative dates.
- Use live authoritative sources for external facts that can change.
- If the user's zone is unknown and changes the answer, ask or state the assumption. Use absolute dates when the difference matters.

## Cross-References

- Read `references/recency-triage.md` to decide whether a prompt needs live verification.
- Read `references/verification-patterns.md` to normalize relative dates and choose sources.
- Read `references/gotchas.md` when stale-memory failures keep recurring.
