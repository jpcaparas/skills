# Temporal Session Brief

- Local now: `{{LOCAL_ISO}}`
- UTC now: `{{UTC_ISO}}`
- Primary timezone: `{{TIMEZONE_PRIMARY}}`
- Relative-date rule: interpret `today`, `yesterday`, and `tomorrow` in this timezone unless the user specifies another one.
- Verification rule: use live sources for volatile external facts such as models, versions, prices, schedules, laws, weather, executives, and current events.
- Refresh rule: rerun the temporal capture if the session crosses midnight, changes timezone context, or rechecks rolling external data.
