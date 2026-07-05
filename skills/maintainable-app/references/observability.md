# Thoughtful Observability

## Table of Contents

- [Purpose](#purpose)
- [Signal Budget](#signal-budget)
- [Structured Logs](#structured-logs)
- [Metrics](#metrics)
- [Traces](#traces)
- [Alerts](#alerts)
- [Dashboards and Runbooks](#dashboards-and-runbooks)
- [Privacy and Cost](#privacy-and-cost)
- [See Also](#see-also)

## Purpose

Read this before adding logs, metrics, traces, dashboards, or alerts. The goal is to explain production behavior and recovery, not to create telemetry volume.

## Signal Budget

For each signal, name the question it answers:

| Signal | Good question |
|---|---|
| Log | What happened to this request/job/event and why did it transition? |
| Metric | Is the system healthy for users and within capacity? |
| Trace | Where did latency or failure cross a boundary? |
| Alert | Does a human need to act because automation is exhausted or users are impacted? |
| Dashboard | Can a solo maintainer understand current state in under a few minutes? |

If the signal does not answer a question, remove it or lower its level.

## Structured Logs

Log decisions and state transitions:

- Request accepted, rejected, deduplicated, degraded, or queued.
- Job leased, started, heartbeated, retried, failed, succeeded, marked stale, or redriven.
- Provider call attempted, timed out, retry scheduled, reconciled, or classified terminal.
- Webhook received, duplicate, invalid, processed, ignored, or failed.
- Circuit breaker, rate limit, load shedding, or graceful degradation activated.

Include stable fields:

```json
{
  "event": "job.retry_scheduled",
  "correlation_id": "req_123",
  "job_id": "job_456",
  "work_key": "report:acct_1:2026-07",
  "attempt": 2,
  "max_attempts": 5,
  "reason": "provider_429",
  "next_run_at": "2026-07-05T09:15:00Z"
}
```

Keep log levels meaningful:

- `debug`: local diagnosis, disabled or sampled in production.
- `info`: normal state transitions and durable decisions.
- `warn`: recovered anomaly, retry scheduled, degraded mode, duplicate delivery.
- `error`: terminal failure or user-impacting failure.
- `fatal`: process cannot continue safely.

Do not log secrets, tokens, cookies, full payment details, raw provider payloads with PII, or user content unless policy explicitly allows it.

## Metrics

Golden rule: start with user-facing health and capacity before bespoke metrics:

- Latency.
- Traffic.
- Errors.
- Saturation.

For any production-facing app change, ask whether these four signals are already measurable for the affected route, job, queue, or dependency. If not, add or route the minimum metric needed before inventing workflow-specific counters.

For app self-healing, add:

| Metric | Why it matters |
|---|---|
| Queue age / oldest pending work | Detects stuck or under-provisioned workers |
| Jobs by status | Shows pending/running/failed/stale/succeeded distribution |
| Retry attempts | Reveals dependency instability and retry storms |
| Dead-letter count | Shows exhausted automation |
| Stale recovered count | Shows watchdog activity |
| Idempotency dedupe count | Shows duplicate input or webhook replays |
| Provider timeout/error rate | Identifies boundary failures |
| Load shed / degraded responses | Shows protected overload |
| Worker saturation | Indicates concurrency caps or capacity pressure |

Avoid high-cardinality labels such as raw user IDs, emails, request paths with IDs, idempotency keys, stack traces, or full provider error messages. Use bounded labels: route template, job type, provider, status, error class, tenant tier, region, and outcome.

## Traces

Trace boundaries and async handoffs:

- HTTP request handler.
- Database transaction.
- External provider call.
- Queue enqueue.
- Worker execution.
- Outbox relay.
- Webhook processing.
- Reconciliation sweep.

Propagate correlation context from request to job and from job to provider calls where the platform supports it. For asynchronous work, persist trace or correlation IDs in the job payload or metadata if safe.

Use semantic conventions when OpenTelemetry is present so traces, metrics, and logs share names across libraries and platforms.

## Alerts

Alert on user impact and exhausted automation:

- Error budget burn or sustained user-visible error rate.
- Oldest queue age above the user promise.
- Dead-letter queue grows above expected poison-message baseline.
- Stale work recovery fails or repeatedly recovers the same work key.
- Provider outage causes degraded mode for critical path.
- Worker saturation persists beyond autoscaling or capacity window.

Do not page for every retry, duplicate webhook, expected provider 429, or single dead-letter item. Those should be visible, searchable, and aggregated first.

Every alert needs:

- User impact.
- Likely cause dimensions.
- First three commands, dashboard links, or queries to inspect.
- Known automatic recovery behavior.
- Manual action only when automation is exhausted.

## Dashboards and Runbooks

For a solo maintainer, dashboards should answer:

1. Are users impacted?
2. Which workflow is failing?
3. Is the system recovering by itself?
4. Which dependency or queue is saturated?
5. What work items are stuck or dead-lettered?
6. What action is safe: wait, redrive, disable feature, scale workers, or fix data?

Keep runbooks short and action-oriented. Prefer admin commands or scripts that validate preconditions over instructions to edit database rows.

## Privacy and Cost

Before adding telemetry:

- Confirm retention and access policy for the data class.
- Redact secrets before logging provider payloads.
- Sample high-volume success logs.
- Aggregate metrics instead of logging every expected success.
- Avoid unbounded labels.
- Make debug logs temporary or feature-flagged.

The best observability is enough to debug the incident without creating a second incident in cost, privacy, or noise.

## See Also

- `principles.md`
- `jobs-and-queues.md`
- `distributed-systems.md`
- `review-rubric.md`
