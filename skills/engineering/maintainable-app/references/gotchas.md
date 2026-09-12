# Gotchas

## Table of Contents

- [Retries](#retries)
- [Queues](#queues)
- [State](#state)
- [Distributed Data](#distributed-data)
- [Observability](#observability)
- [See Also](#see-also)

## Retries

1. Retrying a side effect without idempotency is duplicate-work generation, not resilience.
2. Retrying at the HTTP client, SDK, service layer, job layer, and queue layer can multiply load. Pick one owner when possible.
3. Capped backoff without jitter can synchronize clients at the cap and keep hammering a recovering dependency.
4. Retrying 4xx validation or permission errors usually hides product bugs and delays terminal feedback.
5. A timeout does not prove the remote side effect did not happen. Reconcile or retry with the same idempotency key.

## Queues

1. Unique dispatch does not always mean unique execution. The lock scope and TTL matter.
2. Job timeout must be shorter than queue visibility or retry-after settings. Otherwise a second worker can start before the first is dead.
3. Long jobs without heartbeat cannot distinguish slow progress from a crashed worker.
4. Dead-letter queues without alarms and redrive rules become forgotten storage.
5. Queue length alone can lie. Oldest message age and worker saturation usually reveal stuck processing faster.
6. FIFO ordering can conflict with dead-letter redrive. Preserve ordering only where the business needs it.

## State

1. `pending` needs a creation time, owner, timeout, and next transition.
2. `failed` needs retryability context. Some failures are terminal, some can redrive after a fix, and some require reconciliation first.
3. `canceled` work still needs side-effect rules. Canceling a local job might not cancel provider work already in flight.
4. Free-form status strings spread invalid transitions across the app. Use typed states or centralized transition helpers where the language allows it.

## Distributed Data

1. Publishing an event after committing a database transaction can lose the event if the process crashes.
2. Publishing inside a transaction can publish an event for a transaction that later rolls back.
3. Outbox relays can publish more than once, so consumers still need idempotency.
4. Sagas do not give automatic rollback. Every compensation must be real, safe, and observable.
5. Webhooks can be duplicated, delayed, reordered, or missed. Critical state needs reconciliation.

## Observability

1. Logs that omit work identity are expensive breadcrumbs. Add correlation ID and work key.
2. Logging every success in high-volume paths can become a cost and privacy problem. Prefer metrics and sampled logs.
3. High-cardinality metric labels can make the observability system unstable or expensive.
4. Tracing tiny local functions creates noise. Trace cross-boundary calls and async handoffs.
5. Alerting on expected retries trains the maintainer to ignore alerts. Alert when automation is exhausted or users are impacted.

## See Also

- `principles.md`
- `jobs-and-queues.md`
- `distributed-systems.md`
- `observability.md`
