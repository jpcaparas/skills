# Gotchas

Read this file when the agent keeps sounding current while actually answering from stale memory.

## 1. GPT-4o Drift

**Symptom:** The assistant keeps talking about GPT-4o as if it were the current default family.

**Cause:** Model-family names are volatile, and agents overfit to old high-frequency training patterns.

**Fix:** Treat model names, model pickers, and availability by tier as live data. Verify against official docs before answering. As of April 9, 2026, OpenAI's Help Center documents GPT-5.3 and GPT-5.4 in ChatGPT and notes GPT-4o retirement in ChatGPT.

## 2. UTC Leakage

**Symptom:** `Today` or `tomorrow` is off by one day for the user.

**Cause:** The machine or model silently reasoned in UTC while the user meant local time.

**Fix:** Capture local time first, state the timezone explicitly, and convert relative dates into absolute dates before answering.

## 3. Over-Browsing Stable History

**Symptom:** The agent wastes time verifying fixed historical facts that already include explicit dates.

**Cause:** Recency heuristics are too broad.

**Fix:** Distinguish `Who won the 2024 election?` from `Who is president now?` The first is usually stable; the second is live.

## 4. Fake Freshness

**Symptom:** The answer says `as of now` or `currently` without any live verification.

**Cause:** The language sounds cautious, but the evidence is still internal memory.

**Fix:** Either verify live or remove the freshness claim. Do not imply recency you did not establish.

## 5. Hard-Coded Offsets

**Symptom:** Cross-timezone math fails around DST changes.

**Cause:** The agent used `UTC-5` or `UTC+1` as if it were stable year-round.

**Fix:** Use IANA timezone names and let a real timezone database handle offsets.

## 6. Long-Session Staleness

**Symptom:** Early session timestamps or verified facts are reused hours later with no refresh.

**Cause:** The initial capture step happened once and was never revisited.

**Fix:** Refresh on day boundaries, timezone changes, and before final answers that depend on rolling data. Read `references/long-horizon.md`.
