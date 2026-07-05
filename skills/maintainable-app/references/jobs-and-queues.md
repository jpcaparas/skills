# Jobs, Queues, Webhooks, and Stuck Work

## Table of Contents

- [Purpose](#purpose)
- [Default Job Contract](#default-job-contract)
- [Coalescing Duplicate Work](#coalescing-duplicate-work)
- [Retries, Timeouts, and Leases](#retries-timeouts-and-leases)
- [Stale Work Recovery](#stale-work-recovery)
- [Dead-Letter Handling](#dead-letter-handling)
- [Webhooks](#webhooks)
- [Example: Ten Visitors Start the Same Job](#example-ten-visitors-start-the-same-job)
- [See Also](#see-also)

## Purpose

Read this when building or reviewing queues, background jobs, cron tasks, imports, exports, webhooks, emails, notifications, payment jobs, media processing, or any task that can run outside the original request.

## Default Job Contract

Every production job should answer:

| Question | Required answer |
|---|---|
| What is the durable work identity? | `job_key`, provider event ID, resource ID plus action, or caller idempotency key |
| Can it run twice safely? | Yes through idempotent side effects, or no with a lock/lease plus dedupe |
| What owns concurrency? | Unique constraint, queue deduplication, lock, lease, message group, or partition |
| How long may it run? | Worker timeout and dependency timeouts |
| When is it retried? | Retryable error classes and attempt limits |
| When is it abandoned? | Dead-letter, terminal failed state, or manual review state |
| How is stuck work found? | `lease_expires_at`, `last_heartbeat_at`, `next_run_at`, queue age, or provider status reconciliation |
| What does a user see? | Existing job status, progress, retryable error, or terminal failure |

Do not enqueue anonymous work when the input can be named. A named job can be coalesced, retried, observed, and redriven.

## Coalescing Duplicate Work

For expensive work triggered by users, return an existing active job when the same intent is already queued or running.

```ts
type JobStatus = "pending" | "running" | "succeeded" | "failed" | "stale";

type JobRecord = {
  id: string;
  key: string;
  status: JobStatus;
  attempt: number;
  resultUrl: string | null;
  lastError: string | null;
};

async function enqueueUniqueReportJob(input: {
  accountId: string;
  reportMonth: string;
}): Promise<JobRecord> {
  const key = `report:${input.accountId}:${input.reportMonth}`;

  const existing = await jobs.findActiveByKey(key);
  if (existing) return existing;

  return jobs.createPending({ key, payload: input, maxAttempts: 5 });
}
```

Back this pattern with a unique database constraint or atomic upsert. A read-then-create check without a constraint can still race under concurrent requests.

Framework-specific primitives are useful, but treat them as implementation details:

- Unique job middleware prevents duplicate dispatch or overlapping execution only if the backing lock is configured correctly.
- FIFO queues can preserve per-group order and deduplicate messages, but the deduplication window might be shorter than the business operation.
- Database uniqueness remains the simplest durable backstop for side effects that must happen once.

## Retries, Timeouts, and Leases

Align all timing values:

| Setting | Rule |
|---|---|
| Dependency timeout | Shorter than job timeout; covers connect and request time |
| Job timeout | Shorter than queue retry/visibility window |
| Lock or lease TTL | Longer than normal job runtime, refreshed by heartbeat for long jobs |
| Retry delay | Capped exponential backoff with jitter |
| Max attempts | High enough for transient faults, low enough to reach dead-letter promptly |
| User polling TTL | Long enough to show progress, short enough to avoid stale UI |

If a job can exceed the lock TTL, use heartbeat extension or split the job into smaller resumable units. A stale lock can allow duplicate processing while the first worker is still alive.

Classify errors:

- Retry: network timeout, provider 429/5xx, temporary database connection issue, queue visibility conflict.
- Do not retry unchanged: validation error, missing required resource, permission denial, expired subscription, malformed provider event.
- Reconcile before retry: unknown provider result after timeout, partial upload, payment action, external provisioning action.

## Stale Work Recovery

Add a watchdog or scheduled reconciler for states that can get stuck.

```ts
async function recoverStaleJobs(now: Date): Promise<number> {
  const staleJobs = await jobs.findRunningWithExpiredLease(now);
  let recovered = 0;

  for (const job of staleJobs) {
    if (job.attempt >= job.maxAttempts) {
      await jobs.markFailed(job.id, "lease_expired_max_attempts");
      continue;
    }

    await jobs.releaseForRetry(job.id, {
      nextRunAt: addJitteredBackoff(now, job.attempt),
      reason: "lease_expired",
    });
    recovered += 1;
  }

  return recovered;
}
```

The recovery path must be idempotent. A watchdog might run twice, overlap with a slow worker, or restart mid-sweep.

Track:

- Number of stale jobs found.
- Number retried, failed, or skipped.
- Oldest pending/running age.
- Work keys and job IDs for sampled or anomalous cases.

## Dead-Letter Handling

A dead-letter queue or failed-jobs table needs an operating policy:

- What moves work there: max attempts, poison message, schema failure, terminal provider error.
- What gets stored: work key, payload reference, error code, exception class, attempt count, first/last failure time, correlation ID.
- Who is alerted: user-impacting or growing backlog only, not every expected poison message.
- How redrive works: after code fix, data fix, provider recovery, or explicit operator approval.
- What must never redrive: irreversible side effects without idempotency, malformed malicious input, expired business action.

Keep dead-letter retention longer than the source queue retention when the platform gives you separate settings. Otherwise the diagnostic message can disappear before the maintainer has time to inspect it.

## Webhooks

Webhook providers usually deliver at least once. Design for duplicates and reordering:

1. Verify signature before writing anything.
2. Persist provider event ID in an inbox table with a unique constraint.
3. Return success for already-processed event IDs when the payload matches.
4. Process side effects through idempotent state transitions.
5. Record ignored, duplicate, invalid, and failed events separately.
6. Reconcile with provider APIs when an event implies a state transition but local state is missing.

Do not trust webhook delivery as the only source of truth for money or account access. Use reconciliation for critical provider state.

## Example: Ten Visitors Start the Same Job

If ten users or browser tabs request the same expensive report:

1. Compute `job_key = report:{account_id}:{report_month}`.
2. Attempt an atomic insert into `jobs(job_key)` with a unique constraint.
3. If insert succeeds, enqueue one worker.
4. If insert conflicts, return the existing job ID and status.
5. Worker acquires a lease and updates heartbeat while running.
6. UI polls the shared job status.
7. Watchdog retries jobs whose lease expired and marks exhausted jobs failed.
8. Logs and metrics include `job_id`, `job_key`, `attempt`, `lease_owner`, and outcome.

This avoids ten parallel queues, ten provider calls, and ten copies of the same user-visible result.

## See Also

- `principles.md`
- `distributed-systems.md`
- `observability.md`
- `gotchas.md`
