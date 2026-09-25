# Temporal Session Brief

- Local now: `{{LOCAL_ISO}}`
- UTC now: `{{UTC_ISO}}`
- User timezone (or explicit assumption): `{{USER_TIMEZONE}}`
- Host timezone: `{{TIMEZONE_PRIMARY}}` (not necessarily the user's)
- Relative-date rule: use the user's timezone for `today`, `yesterday`, and `tomorrow`.
- Verification rule: use live sources for volatile external facts such as models, versions, prices, schedules, laws, weather, executives, and current events.
- Refresh rule: reuse a sufficient fresh anchor; capture when missing, stale, or relevant boundary math matters. Recheck rolling external evidence separately.
