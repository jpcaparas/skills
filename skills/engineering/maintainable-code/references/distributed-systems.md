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

Ensure bounded waits at applicable boundaries, accounting for effective framework or platform deadlines before adding another timeout layer:

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

When duplicates could cause harmful side effects, establish idempotency at the enforcing boundary. Existing resource semantics, uniqueness, or provider guarantees may suffice. When using explicit idempotency keys:

- Accept or generate an idempotency key for side-effecting operations.
- Persist the key with caller identity, request intent, parameters, status, and response summary.
- Reject reuse of the same key for materially different intent.
- Return a semantically equivalent result for a replay.
- Expire keys only after the retry window and provider uncertainty window have passed.
- Include the idempotency key in logs and traces, but not if it contains sensitive data.

Do not infer idempotency only by comparing payloads. Identical payloads can represent separate user intent.

## Outbox and Inbox

Ensure a required event or side-effect handoff cannot be silently lost after a database change. An outbox is one option when existing transactional messaging or a proven reconciliation path does not already provide that guarantee:

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

Use an inbox table when harmful duplicates are not already prevented by idempotent consumer effects or durable deduplication. If needed:

- Unique key: `consumer_name + message_id`.
- Store received, processed, failed, and ignored states.
- Process the message and mark it processed in one local transaction when possible.

## Sagas and Compensation

Define safe partial-completion outcomes when a business workflow spans services or databases without one ACID transaction. Use a saga when coordinated recovery warrants it; an existing workflow or a simple terminal failure path may suffice.

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

Resolve uncertain external outcomes safely. Use an existing provider lookup, same-key idempotent retry, or recovery workflow when sufficient; add reconciliation for otherwise unresolved cases such as:

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
- Provides enough evidence to diagnose drift and recovery, reusing existing signals where adequate.

## See Also

- `resilience.md`
- `jobs-and-queues.md`
- `observability.md`
- `gotchas.md`
