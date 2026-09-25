# Recency Triage

Read this file when you need to decide whether a prompt is stable, system-clock-sensitive, or live-verification-required.

## Classification Table

| Prompt shape | Category | Live verification | Action |
| --- | --- | --- | --- |
| "What's today's date?" | System clock | No | Reuse a fresh reliable clock in the user's timezone; capture if insufficient |
| "What time is it in New York right now?" | System clock | No | Run `scripts/capture_temporal_context.py --extra-zone America/New_York` |
| "What is the latest OpenAI model for coding?" | Volatile external fact | Yes | Use a sufficient time anchor, then verify against current official docs |
| "What's Tesla stock price today?" | Volatile external fact | Yes | Establish the relevant date, then verify against a live finance source |
| "Who is the CEO of OpenAI now?" | Volatile external fact | Yes | Verify live before answering |
| "Who won the 2024 US presidential election?" | Stable historical fact | Usually no | Answer directly, but keep the explicit year in view |
| "Explain the TCP three-way handshake." | Timeless explanation | No | Do not force temporal tooling |

## Heuristics

### Signals to assess for live verification

- The prompt contains `latest`, `current`, `currently`, `today`, `yesterday`, `tomorrow`, `recent`, `recently`, `as of`, `now`, or `still`.
- The prompt asks about models, versions, releases, pricing, laws, regulations, scores, schedules, weather, elections-in-progress, executives, or live company facts.
- The user asks for current source-backed confirmation not already supported by fresh evidence.

These are not automatic browsing triggers. "Explain the current function below" or "Summarize yesterday's attached notes" can be answered from supplied evidence. Browse when the answer actually asserts a changing external fact; assess citation requests by the evidence they need.

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

1. Identify the claim and evidence needed; run `python3 scripts/recency_guard.py --prompt "..." --format markdown` only if its advisory classification helps.
2. For truly volatile external claims, verify live with authoritative sources or state that verification is unavailable.
3. For clock-only questions, use a fresh reliable anchor in the relevant user timezone. Capture if missing, stale, or boundary math matters.
4. For stable or fully supplied information, answer directly. The guard can over-flag explicit historical years as `system-clock` or time words as `live-verify`; reasoned assessment overrides these heuristic labels, not real evidence requirements.

## Cross-References

- Read `references/bootstrap.md` for the startup sequence.
- Read `references/verification-patterns.md` for answer-shaping rules after classification.
- Read `references/long-horizon.md` if the session may outlive the first classification pass.
