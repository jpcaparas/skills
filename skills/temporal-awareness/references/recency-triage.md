# Recency Triage

Read this file when you need to decide whether a prompt is stable, system-clock-sensitive, or live-verification-required.

## Classification Table

| Prompt shape | Category | Live verification | Action |
| --- | --- | --- | --- |
| "What's today's date?" | System clock | No | Run `scripts/capture_temporal_context.py` and answer from the local clock |
| "What time is it in New York right now?" | System clock | No | Run `scripts/capture_temporal_context.py --extra-zone America/New_York` |
| "What is the latest OpenAI model for coding?" | Volatile external fact | Yes | Capture the clock, then verify against current official docs |
| "What's Tesla stock price today?" | Volatile external fact | Yes | Capture the date, then verify against a live finance source |
| "Who is the CEO of OpenAI now?" | Volatile external fact | Yes | Verify live before answering |
| "Who won the 2024 US presidential election?" | Stable historical fact | Usually no | Answer directly, but keep the explicit year in view |
| "Explain the TCP three-way handshake." | Timeless explanation | No | Do not force temporal tooling |

## Heuristics

### Treat as live-verification-required

- The prompt contains `latest`, `current`, `currently`, `today`, `yesterday`, `tomorrow`, `recent`, `recently`, `as of`, `now`, or `still`.
- The prompt asks about models, versions, releases, pricing, laws, regulations, scores, schedules, weather, elections-in-progress, executives, or live company facts.
- The user asks for links, quotes, or source-backed confirmation.

### Treat as system-clock-sensitive

- The prompt is about local date, time, timezone, day boundaries, or cross-zone conversion.
- The answer depends on what `today` means locally, but not on external changing facts.

### Treat as stable

- The prompt is timeless or historical and includes an explicit date or year.
- The answer would remain correct even if checked tomorrow.

## Override Rules

1. Relative-time language beats weak historical hints. `Who is president today?` is live, even if the prompt also mentions a year.
2. Explicit dates lower risk. `What happened on 2024-11-05?` is usually stable unless the user asks for later consequences or current status.
3. Company roles are volatile. `Who is the CEO now?` requires live verification. `Who was the CEO in 2022?` usually does not.
4. Model families and product limits are volatile. Treat them like pricing or release data, not like timeless definitions.

## Practical Workflow

1. Run `python3 scripts/recency_guard.py --prompt "..." --format markdown`.
2. If it says `live-verify`, browse or search authoritative sources before answering.
3. If it says `system-clock`, answer from the captured local/UTC time context.
4. If it says `stable`, answer normally and avoid wasting time on unnecessary browsing.

## Cross-References

- Read `references/bootstrap.md` for the startup sequence.
- Read `references/verification-patterns.md` for answer-shaping rules after classification.
- Read `references/long-horizon.md` if the session may outlive the first classification pass.
