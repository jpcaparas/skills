---
name: temporal-awareness
description: "Use this skill when the user asks for the latest, current, recent, today, yesterday, tomorrow, this week, current events, new models, versions, prices, schedules, executives, laws, or anything else that may have changed after pretraining. It grounds the session in the real system clock and timezone, triages whether live verification is mandatory, converts relative dates into absolute dates, and prevents stale-memory answers such as repeating retired model families. Triggers on: latest, current, today, yesterday, tomorrow, recent, as of now, current model, release, version, price, schedule, CEO, president, weather, score. Do NOT trigger for stable historical facts with explicit dates, timeless explanations, or pure writing tasks with no time sensitivity."
compatibility: "Requires: python3. Optional: web/search tooling for live verification of volatile claims."
---

# temporal-awareness

Ground the session in the real clock before answering anything that could have changed.

Verified locally on April 9, 2026 in Pacific/Auckland (NZST, UTC+12). The motivating failure mode is real: OpenAI's official Help Center now documents GPT-5.3 and GPT-5.4 in ChatGPT, while stale assistants still default to GPT-4o-era wording from older memory.

## Decision Tree

What is the time-sensitive failure mode?

- Need a clean session anchor before answering
  - Run `python3 scripts/capture_temporal_context.py --format markdown`
  - Read `references/bootstrap.md`

- Need to decide whether a prompt can be answered from stable knowledge or needs live verification
  - Run `python3 scripts/recency_guard.py --prompt "..." --format markdown`
  - Read `references/recency-triage.md`

- Need patterns for `latest`, `today`, `yesterday`, `tomorrow`, timezone math, or source selection
  - Read `references/verification-patterns.md`

- Need refresh rules for long-running sessions, day rollovers, or recurring work
  - Read `references/long-horizon.md`

- Need to debug stale assumptions, outdated model names, or relative-date mistakes
  - Read `references/gotchas.md`

## Quick Reference

| Task | Command or file | Why |
| --- | --- | --- |
| Capture local and UTC time context | `python3 scripts/capture_temporal_context.py --format markdown` | Load the real clock into the session before answering |
| Compare the current moment across zones | `python3 scripts/capture_temporal_context.py --format markdown --extra-zone America/New_York --extra-zone Europe/London` | Avoid silent timezone drift |
| Classify whether a prompt needs live verification | `python3 scripts/recency_guard.py --prompt "What is the latest OpenAI model for coding?" --format markdown` | Separate stable questions from volatile ones |
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
| "Why are agents still mentioning GPT-4o / old CEOs / stale prices?" | `references/gotchas.md` |

## Operational Rules

1. Run `scripts/capture_temporal_context.py` before answering any prompt that uses relative time language or depends on the current date, time, or timezone.
2. Run `scripts/recency_guard.py` on prompts containing `latest`, `current`, `today`, `yesterday`, `tomorrow`, `recent`, `as of`, or volatile domains such as models, prices, laws, schedules, weather, executives, or live events.
3. Treat the system clock as authoritative for local date and time, but treat external current facts as untrusted until verified against live sources.
4. Convert relative dates into absolute dates before answering whenever there is even a small chance the user is thinking in a different timezone.
5. Refresh the temporal anchor when the session crosses midnight, spans multiple hours, changes timezone context, or revisits rolling external data.

## Verified Behaviors

1. `scripts/capture_temporal_context.py` emits local and UTC timestamps, timezone name candidates, UTC offset, locale, platform, and optional extra-zone snapshots.
2. `scripts/recency_guard.py` detects relative-date language and volatile domains, and distinguishes stable historical prompts from current-state prompts.
3. `scripts/probe_temporal_awareness.py` runs deterministic checks across smoke, edge, negative, and disclosure-style scenarios.
4. The skill explicitly treats model families and product versions as volatile; this prevents stale answers like defaulting to GPT-4o when the official docs have moved on.
5. Long-running sessions get explicit refresh rules instead of assuming the first temporal anchor stays valid forever.

## Gotchas

1. **Do not confuse clock grounding with live verification**: the system clock can tell you what day it is locally, but it cannot tell you today's stock price or the current CEO.
2. **Relative dates are timezone-dependent**: `today`, `yesterday`, and `tomorrow` are wrong if you silently assume UTC while the user is thinking locally.
3. **Historical facts are not the same as current-state facts**: `Who won the 2024 election?` is usually stable; `Who is president now?` is not.
4. **Model names drift faster than agents admit**: treat model families, versions, limits, and availability as volatile unless you just verified them.
5. **Long sessions go stale**: if work spans a day boundary or a DST change, rerun the capture step and restate the new absolute date.

## Helper Scripts

- `scripts/capture_temporal_context.py` prints a session-ready time anchor in JSON, text, or Markdown.
- `scripts/recency_guard.py` classifies a prompt as stable, system-clock-sensitive, or live-verification-required.
- `scripts/probe_temporal_awareness.py` runs deterministic regression checks across the core heuristics.
- `scripts/validate.py` validates structure, references, eval coverage, and Python syntax.
- `scripts/test_skill.py` validates the packaging and runs the temporal probe suite.
