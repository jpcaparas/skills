# Distributed Systems Resilience

## Table of Contents

- [Purpose](#purpose)
- [Timeouts](#timeouts)
- [Retries](#retries)
- [Idempotent APIs](#idempotent-apis)
- [Outbox and Inbox](#outbox-and-inbox)
- [Sagas and Compensation](#sagas-and-compensation)
- [Backpressure and Isolation](#backpressure-and-isolation)
- [Reconciliation](#reconciliation)
- [See Also](#see-also)

## Purpose

Read this when a feature crosses process, network, database, provider, queue, or service boundaries. The goal is to keep partial failure from becoming duplicate side effects, stuck state, or a developer-only repair task.

## Timeouts

Set timeouts at every boundary:

- Connection timeout: cannot establish the connection.
- Request timeout: remote call did not finish.
- Transaction timeout: database work held locks too long.
- Job timeout: worker exceeded its budget.
- Lease timeout: owner stopped heartbeating.
- User timeout: UI stops waiting and shows async status.

Timeouts should be shorter than the next outer budget. A dependency call should time out before the job does; the job should time out before queue visibility expires; the user request should stop waiting before the load balancer does.

## Retries

Retries are for transient failures, not uncertainty. Use this default:

| Error | Action |
|---|---|
| Validation, auth, permission, missing required input | Do not retry unchanged |
| 429 or provider rate limit | Retry after provider hint or capped jittered backoff |
| 5xx, network reset, temporary DNS, timeout | Retry if the operation is idempotent or read-only |
| Unknown result after side-effecting timeout | Reconcile or retry with the same idempotency key |
| Overload inside your app | Shed load, queue, or degrade before retrying |

Retry in one layer where practical. Retries at every layer multiply load and can prevent recovery.

Use retry budgets:

```ts
type RetryPolicy = {
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
};

function nextRetryDelayMs(policy: RetryPolicy, attempt: number): number {
  const exponential = policy.baseDelayMs * 2 ** Math.max(0, attempt - 1);
  const capped = Math.min(exponential, policy.maxDelayMs);
  return Math.floor(capped * (0.5 + Math.random()));
}
```

For scheduled or periodic work, add stable jitter so every tenant or worker does not fire at the same second.

## Idempotent APIs

When designing an internal API or calling an external provider:

- Accept or generate an idempotency key for side-effecting operations.
- Persist the key with caller identity, request intent, parameters, status, and response summary.
- Reject reuse of the same key for materially different intent.
- Return a semantically equivalent result for a replay.
- Expire keys only after the retry window and provider uncertainty window have passed.
- Include the idempotency key in logs and traces, but not if it contains sensitive data.

Do not infer idempotency only by comparing payloads. Identical payloads can represent separate user intent.

## Outbox and Inbox

Use an outbox when a database change must publish an event or enqueue a side effect:

```text
HTTP request
  -> database transaction
       -> update business row
       -> insert outbox row
  -> relay publishes outbox row
  -> consumer deduplicates by message ID
```

Outbox rules:

- Insert the outbox row in the same transaction as the business state change.
- Relay outbox rows asynchronously with retry and ordering rules where needed.
- Make consumers idempotent because relays and brokers can publish or deliver more than once.
- Store relay attempts, last error, and next run time.
- Avoid deleting outbox rows before metrics and audit needs are satisfied.

Use an inbox table on consumers when duplicate messages would cause harm:

- Unique key: `consumer_name + message_id`.
- Store received, processed, failed, and ignored states.
- Process the message and mark it processed in one local transaction when possible.

## Sagas and Compensation

Use a saga when a business workflow spans services or databases and cannot rely on one ACID transaction.

Model:

- Local transaction updates local state.
- Message or command triggers the next step.
- Failure invokes a compensating action or terminal state.
- Caller can query the saga outcome asynchronously.

Be explicit about compensation. "Rollback" is not automatic:

- Payment authorized -> void authorization.
- Inventory reserved -> release reservation.
- Account provisioned -> disable account and mark cleanup required.
- Email sent -> cannot unsend; compensate with follow-up or account note.

Use orchestration when central visibility and recovery matter more than loose coupling. Use choreography only when event flows are simple enough to inspect during an incident.

## Backpressure and Isolation

Protect shared systems:

- Queue-based load leveling buffers bursts.
- Competing consumers scale throughput behind worker caps.
- Rate limits protect providers and internal dependencies.
- Bulkheads isolate connection pools, worker pools, tenants, queues, or feature classes.
- Circuit breakers can stop known-bad calls, but require careful testing because they introduce modes.
- Load shedding drops lower-priority work early so the app can recover.

Pick limits in business terms when possible: per account, per user, per provider, per workflow, or per queue. Global limits alone can let one tenant starve everyone else.

## Reconciliation

Add reconciliation when the local app cannot know whether an external side effect happened:

- Payment status after provider timeout.
- Email provider accepted request but local worker crashed.
- File upload completed but database update failed.
- Webhook missed or arrived before related local state.
- Outbox relay published but crashed before marking the row.

Reconciliation job checklist:

- Queries provider or durable local source of truth.
- Uses a bounded time window and pagination.
- Records what changed and why.
- Is safe to run repeatedly.
- Emits metrics for drift found, fixed, and skipped.

## See Also

- `principles.md`
- `jobs-and-queues.md`
- `observability.md`
- `gotchas.md`
