---
name: maintainable-app
description: "Passive production-app resilience skill for self-healing apps. Use when coding or reviewing features with jobs, queues, webhooks, persistence, APIs, retries, concurrency, logging, tracing, observability, incidents, edge cases, failsafes, idempotency, backpressure, graceful degradation, or stuck jobs. Do NOT use for non-code writing, throwaway scripts, or visual-only mockups."
compatibility: "No external dependencies. Optional helper scripts require python3."
metadata:
  version: "1.0.0"
  short-description: "Build self-healing apps with thoughtful failsafes and observability"
  openclaw:
    category: "development"
    requires:
      bins: [python3]
references:
  - principles
  - jobs-and-queues
  - distributed-systems
  - observability
  - review-rubric
  - gotchas
  - source-notes
---

# maintainable-app

Build, edit, and review applications so common production failures recover automatically, degrade intentionally, and leave enough signal for one maintainer to understand what happened.

## Passive Trigger

Load this skill in the background whenever a coding task affects a production-facing application, background worker, scheduled task, webhook, payment flow, import/export, notification, API integration, database state transition, cache, file upload, queue, cron, auth/session flow, observability, logging, tracing, alerting, or reliability behavior.

Keep it lightweight for small changes: run a quick failure-mode pass silently, then mention only the failsafes, edge cases, and observability decisions that change the implementation. Also load {{ skill:maintainable-code }} for source-code changes and {{ skill:maintainable-tests }} when adding or changing tests, if available.

## Decision Tree

What are you building or changing?

- User-facing request, workflow, or state transition:
  Read `references/principles.md`. Define the failure states, retry safety, user-visible fallback, and recovery path before coding the happy path.

- Queue, background job, cron, webhook, import/export, email, payment capture, or notification:
  Read `references/jobs-and-queues.md`. Require idempotency, unique work identity, bounded concurrency, retry limits, dead-letter handling, stale-work recovery, and worker timeouts.

- Multiple services, external APIs, event publishing, distributed data changes, or async workflows:
  Read `references/distributed-systems.md`. Design timeouts, retry budgets, outbox/inbox handling, deduplication, reconciliation, and compensating actions.

- Logging, metrics, tracing, alerts, dashboards, or incident diagnosis:
  Read `references/observability.md`. Instrument the decision points that explain user impact and recovery, not every line of code.

- Reviewing a diff or implementation plan:
  Use `references/review-rubric.md`. Lead with failures that would require manual developer intervention, duplicate side effects, stuck states, unbounded retries, and missing operational signal.

- Unsure where to start:
  Read `references/principles.md`, then run the Self-Healing Gate below.

## Quick Reference

| Situation | Default action |
|---|---|
| Duplicate browser submit, webhook replay, retry, or worker restart | Add an idempotency key or deterministic work key and persist the result or state transition |
| Ten users trigger the same expensive job | Coalesce by unique job key, lease one active worker, return the existing job status, and expose progress |
| Job stays `pending` or `running` too long | Add `expires_at` or heartbeat-based stale detection, safe retry or failover, and an audit log entry |
| Remote API call | Set connection and request timeouts, classify retryable errors, use capped backoff with jitter, and stop at a retry budget |
| Queue load spike | Buffer work, cap worker concurrency, use backpressure/rate limits, and protect shared dependencies |
| Side effect after database write | Use an outbox or transactional handoff; make consumers idempotent |
| Multi-step distributed workflow | Model states explicitly and add reconciliation or compensating actions |
| Partial outage | Degrade lower-value features first and preserve the core user task |
| Logging request/job progress | Include correlation ID, actor, work key, state transition, attempt, dependency, duration, and outcome |
| Metrics | Track latency, traffic, errors, saturation, queue age, retry count, dead-letter count, and stale work |
| Tracing | Add spans around cross-boundary calls and durable async handoffs, not tiny local helpers |
| Alert | Page only on user impact or exhausted automation; otherwise create inspectable dashboards or tickets |

## Core Rules

1. Treat retries, duplicate delivery, concurrency, latency, partial failure, deploy restarts, and stale state as normal inputs, not unusual accidents.
2. Give every expensive or side-effecting operation a stable identity. The system should know whether a request is new work, a replay, or a different intent.
3. Prefer explicit state machines over loose status strings. Each state needs allowed transitions, owner, timeout, retry policy, terminal outcomes, and recovery behavior.
4. Put recovery in the application before putting it in a human runbook. Use bounded retries, stale-work sweepers, reconciliation jobs, dead-letter queues, and safe redrive paths.
5. Limit blast radius with queues, leases, rate limits, bulkheads, and backpressure. Do not let one noisy workflow exhaust the whole app.
6. Make side effects idempotent at the boundary that can enforce it: database constraints, unique keys, idempotency tables, outbox/inbox tables, provider idempotency keys, or queue deduplication.
7. Use timeouts everywhere work crosses process, network, queue, database, or provider boundaries. A stuck dependency should become a known state with a bounded recovery path.
8. Golden rule: every production-facing app change should consider the four golden signals first: latency, traffic, errors, and saturation. Add bespoke metrics only after those user-health and capacity questions are covered.
9. Log and trace for decisions, state transitions, retries, dropped work, degraded behavior, and dependency boundaries. Do not add telemetry that cannot answer a production question.
10. Keep logs safe to retain and search. Never log secrets, tokens, raw payment details, full PII, session cookies, or provider credentials.
11. Test the recovery path. A feature is not operationally ready until duplicate requests, retryable failures, stuck jobs, dependency timeouts, and stale state have focused verification or a documented gap.

## Self-Healing Gate

Before finishing an app change, check:

| Gate | Pass condition |
|---|---|
| Identity | Duplicate requests, jobs, webhooks, and events map to a stable idempotency or work key |
| State | Non-trivial work has explicit pending/running/succeeded/failed/canceled/stale behavior |
| Concurrency | Shared resources have uniqueness, locking, leases, rate limits, or worker caps |
| Time | Remote calls, jobs, locks, and pending states have timeouts or expiration |
| Retries | Retryable errors are classified, bounded, jittered, and safe against duplicate side effects |
| Recovery | Stuck, partial, and failed states can be retried, reconciled, redriven, or made terminal without a developer editing data by hand |
| Degradation | The app preserves the most important user task when optional dependencies fail |
| Observability | Logs, metrics, and traces explain user impact, work identity, state transitions, attempts, dependency health, and recovery outcomes |
| Alerts | Alerts fire on exhausted automation or user impact, not on every expected transient failure |
| Tests | The most likely production failure has a focused test, simulation, or stated verification gap |

## Operating Workflow

1. Recon first.
   Read the surrounding handlers, jobs, schemas, provider adapters, queue config, logging conventions, dashboards, and tests before designing resilience.

2. Draw the failure map.
   List duplicate input, concurrent input, dependency timeout, provider 429/5xx, worker crash, deploy restart, database conflict, stale state, and partial completion. Keep the list proportional to feature risk.

3. Choose the recovery owner.
   Decide whether the request handler, queue worker, scheduler, reconciliation job, database constraint, provider idempotency feature, or operator-facing tool owns each recovery path.

4. Implement the smallest durable mechanism.
   Prefer local constraints and existing framework primitives. Add queues, locks, outbox tables, circuit breakers, or watchdogs when the failure mode is real enough to justify them.

5. Instrument the story.
   Add structured logs, metrics, and spans at state transitions and boundaries. Name the specific question each signal answers.

6. Verify failure behavior.
   Run focused tests or local simulations for duplicate input, retry, timeout, stale work, and degraded dependency behavior where practical.

7. Report plainly.
   Name the edge cases handled, the failsafes added, the signals added, verification run, and remaining operational risks.

## Optional Helper

Use the helper as a fast review prompt scanner, not as a verdict:

```bash
python3 scripts/analyze_app_resilience.py /path/to/project
python3 scripts/analyze_app_resilience.py /path/to/project --json
```

It flags likely missing idempotency, retry/backoff gaps, external calls without obvious timeouts, low-context logs, swallowed errors, and pending states without recovery. A quiet scan does not prove the app is resilient, and a noisy scan does not prove the code is wrong.

## Reading Guide

| Need | Read |
|---|---|
| Core self-healing principles and failure mapping | `references/principles.md` |
| Jobs, queues, webhooks, cron, stuck work, and duplicate work | `references/jobs-and-queues.md` |
| Retries, timeouts, idempotent APIs, outbox/inbox, sagas, and reconciliation | `references/distributed-systems.md` |
| Logging, metrics, tracing, alerts, and dashboards | `references/observability.md` |
| Severity-first review of resilience diffs | `references/review-rubric.md` |
| Common traps and anti-patterns | `references/gotchas.md` |
| Research sources and adaptation notes | `references/source-notes.md` |

## Gotchas

1. Retrying unsafe work can create the outage you were trying to heal. Make the operation idempotent before adding retries.
2. A unique job is not enough if the lock expires before the worker finishes. Align lock TTL, job timeout, visibility timeout, and retry window.
3. `pending` is not a recovery strategy. Every non-terminal state needs an owner and a stale-state path.
4. Logs without correlation IDs, work keys, attempts, and outcomes rarely help during a solo-maintainer incident.
5. More observability is not automatically better. High-cardinality, secret-bearing, or unqueried telemetry creates cost and risk without improving recovery.
6. Dead-letter queues are not trash cans. They need alarms, inspection fields, redrive rules, and a policy for poison messages.
7. Graceful degradation must be implemented before the outage. Optional features should fail small while the core task still works.
