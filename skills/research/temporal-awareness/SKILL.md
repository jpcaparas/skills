---
name: temporal-awareness
description: "Use for latest/current/recent/today/yesterday/tomorrow questions, changing models, versions, prices, schedules, executives, laws, weather, scores, or other time-sensitive facts. Not for stable history."
---

# temporal-awareness

Anchor time-sensitive answers to the real clock and the user's timezone, and verify changing external facts live instead of answering from memory.

- **A clock does not verify facts.** `date` (or the session's own clock) says what day it is; it cannot say the current model, version, price, CEO, law, schedule, weather or score. For those, use a live authoritative source, or say you could not verify. Never write "currently" or "as of now" on the strength of memory.
- **Model names, versions, limits and availability drift faster than you expect.** Verify them against official docs unless just verified; do not infer a replacement or rollout from memory.
- **Stable history needs no check.** "Who won the 2024 election?" is fixed; "Who is president now?" is live. Do not browse, dump clocks or run tools just because a prompt contains a time word.
- **The user's timezone governs relative dates**, not the orb or server zone. Use IANA names (`TZ=Pacific/Auckland date`), never hard-coded offsets like `UTC-5`, which break across DST. If a consequential timezone is unknown, ask or state the assumption; do not infer it from the host.
- **Convert relative dates to absolute ones** ("Friday 2026-11-13") when ambiguity or a day boundary matters, and in anything the user will act on later.
- **Reuse a fresh, reliable clock** when you have one. Capture a new one when it is missing or stale, or when midnight, DST or cross-zone boundaries matter.
- **Long sessions go stale.** After long pauses, a day rollover in the user's zone, a DST change or a timezone change, refresh the anchor and any rolling external data before a final answer that depends on them.
- When live verification is unavailable, state the limitation instead of asserting currentness.
