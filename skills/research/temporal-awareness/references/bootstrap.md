# Bootstrap

Read this file when you need to load the real date, time, and timezone into the session before answering.

## Session-Start Protocol

1. Capture the current local and UTC clock state.

```bash
python3 scripts/capture_temporal_context.py --format markdown
```

2. If the user's prompt already exists, classify the recency risk before answering.

```bash
python3 scripts/recency_guard.py --prompt "What is the latest OpenAI model for coding?" --format markdown
```

3. If the guard says `requires_live_verification: true`, verify against current authoritative sources before answering.
4. If the prompt contains `today`, `yesterday`, `tomorrow`, `this week`, or similar language, restate the relevant absolute dates and timezone in the answer.
5. If the session spans hours or crosses midnight, rerun the capture step. Read `references/long-horizon.md` for refresh rules.

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
| `session_directives` | Ready-to-apply rules for the rest of the session |

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

- Use the system clock for local time, date, and timezone.
- Use live authoritative sources for external facts that can change.
- Use absolute dates in the answer whenever the user might be thinking in a different timezone than the machine.

## Cross-References

- Read `references/recency-triage.md` to decide whether a prompt needs live verification.
- Read `references/verification-patterns.md` to normalize relative dates and choose sources.
- Read `references/gotchas.md` when stale-memory failures keep recurring.
