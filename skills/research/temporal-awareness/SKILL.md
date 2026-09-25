---
name: temporal-awareness
description: "Use for latest/current/recent/today/yesterday/tomorrow questions, changing models, versions, prices, schedules, executives, laws, weather, scores, or other time-sensitive facts. Ground answers in clock and timezone, verify live when needed, and convert relative dates. Do NOT use for stable history."
compatibility: "Python3 for bundled helpers. Web/search tools for live verification of volatile external claims; a sufficient session clock needs no helper run."
---

# temporal-awareness

Use a reliable time anchor and the user's timezone for time-sensitive answers; verify changing external facts separately.

## Decision Tree

What is the time-sensitive failure mode?

- Need a clean session anchor before answering
  - Reuse a fresh, reliable session clock and known user timezone when sufficient.
  - If missing, stale, or boundary math matters, run `python3 scripts/capture_temporal_context.py --format markdown` (add `--extra-zone <user-zone>` when needed). Read `references/bootstrap.md` for details.

- Need to decide whether a prompt can be answered from stable knowledge or needs live verification
  - Reason from the claim's volatility and available evidence. `scripts/recency_guard.py` is an optional advisory heuristic, not a required command or a substitute for judgment.
  - Read `references/recency-triage.md` when the distinction is unclear.

- Need patterns for `latest`, `today`, `yesterday`, `tomorrow`, timezone math, or source selection
  - Read `references/verification-patterns.md`

- Need refresh rules for long-running sessions, day rollovers, or recurring work
  - Read `references/long-horizon.md`

- Need to debug stale assumptions, outdated model names, or relative-date mistakes
  - Read `references/gotchas.md`

## Quick Reference

| Task | Command or file | Why |
| --- | --- | --- |
| Capture missing or stale local and UTC time context | `python3 scripts/capture_temporal_context.py --format markdown` | Establish a reliable anchor when existing context is insufficient |
| Compare the current moment across zones | `python3 scripts/capture_temporal_context.py --format markdown --extra-zone America/New_York --extra-zone Europe/London` | Avoid silent timezone drift |
| Get an advisory recency classification | `python3 scripts/recency_guard.py --prompt "What is the latest release?" --format markdown` | Flag risks to assess, not a mandatory decision gate |
| Run the deterministic probe suite | `python3 scripts/probe_temporal_awareness.py --format pretty` | Verify the skill still behaves as designed |
| Learn the startup workflow | `references/bootstrap.md` | Session-load order and exact commands |
| Handle relative dates and volatile facts | `references/verification-patterns.md` | Absolute-date conversion and source selection |

## Reading Guide

| If the user says... | Read |
| --- | --- |
| "Before you answer, what date is it here and what timezone are we using?" | `references/bootstrap.md` |
| "Do I need to browse for this or is it stable?" | `references/recency-triage.md` |
| "What does latest mean here?" | `references/verification-patterns.md` |
| "This session has been running for hours, should we refresh the date context?" | `references/long-horizon.md` |
| "Why are agents still mentioning outdated products, roles, or prices?" | `references/gotchas.md` |

## Operational Rules

1. Check whether the session already has a reliable clock fresh enough for the requested precision. Reuse it when sufficient; capture when missing or stale, or when midnight, DST, or cross-zone boundary calculations matter.
2. The user's known timezone governs user-relative dates, not the orb/server's local timezone. Use IANA zones for conversions. If a consequential timezone is unknown, ask or state the assumption instead of inferring it from the host.
3. Use live authoritative sources for truly volatile external claims: current models, versions, prices, laws, schedules, weather, executives, and live events. A clock does not verify these facts. If live verification is unavailable, state that limitation rather than asserting currentness.
4. Convert relative dates into explicit dates when ambiguity or a boundary matters. Do not add clock dumps, tool runs, or browsing solely because a prompt contains a time word.
5. Reassess freshness after long pauses, user-zone midnight, DST changes, or a timezone-context change. Refresh only what the answer needs; rolling external data may need a new source check even while the clock anchor remains sufficient.

## Verified Behaviors

1. `scripts/capture_temporal_context.py` emits local and UTC timestamps, timezone name candidates, UTC offset, locale, platform, and optional extra-zone snapshots.
2. `scripts/recency_guard.py` detects relative-date language and volatile domains, and distinguishes stable historical prompts from current-state prompts.
3. `scripts/probe_temporal_awareness.py` runs deterministic checks across smoke, edge, negative, and disclosure-style scenarios.
4. The skill treats model families and product versions as volatile rather than assuming remembered defaults remain current.
5. Long-running sessions get explicit refresh rules instead of assuming the first temporal anchor stays valid forever.

## Gotchas

1. **Do not confuse clock grounding with live verification**: the system clock can tell you what day it is locally, but it cannot tell you today's stock price or the current CEO.
2. **Relative dates are timezone-dependent**: `today`, `yesterday`, and `tomorrow` are wrong if you silently assume UTC while the user is thinking locally.
3. **Historical facts are not the same as current-state facts**: `Who won the 2024 election?` is usually stable; `Who is president now?` is not.
4. **Model names drift faster than agents admit**: treat model families, versions, limits, and availability as volatile unless you just verified them.
5. **Long sessions go stale**: if work spans a relevant day boundary or DST change, refresh the anchor and restate the date when needed.

## Keeping Guidance Current

When a gap or suspected staleness affects the task, consult current official clock/timezone/tool documentation or trusted sources appropriate to the claim. Skip routine browsing when the evidence is sufficient. If sources are unavailable, state the gap; propose a sourced correction with an example or check in the canonical package, never an automatic edit to installed copies.

## Helper Scripts

- `scripts/capture_temporal_context.py` prints a session-ready time anchor in JSON, text, or Markdown.
- `scripts/recency_guard.py` classifies a prompt as stable, system-clock-sensitive, or live-verification-required.
- `scripts/probe_temporal_awareness.py` runs deterministic regression checks across the core heuristics.
- `scripts/validate.py` validates structure, references, eval coverage, and Python syntax.
- `scripts/test_skill.py` validates the packaging and runs the temporal probe suite.
