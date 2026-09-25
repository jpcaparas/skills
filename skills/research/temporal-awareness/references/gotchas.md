# Gotchas

Read this file when the agent keeps sounding current while actually answering from stale memory.

## 1. Product-Version Drift

**Symptom:** The assistant treats a remembered model family or product version as the current default.

**Cause:** Model-family names are volatile, and agents overfit to old high-frequency training patterns.

**Fix:** Verify current model names, pickers, and availability against official docs. Hypothetically, a remembered "Model A" default may have been replaced by "Model B"; do not infer the replacement or rollout from memory.

## 2. UTC Leakage

**Symptom:** `Today` or `tomorrow` is off by one day for the user.

**Cause:** The machine or model silently reasoned in UTC while the user meant local time.

**Fix:** Use the known user's timezone rather than the orb/server's local zone. Reuse a sufficient anchor or capture when needed, and state absolute dates when the boundary matters.

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
