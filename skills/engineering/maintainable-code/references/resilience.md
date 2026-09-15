# Self-Healing Application Principles

## Table of Contents

- [Purpose](#purpose)
- [Failure-First Design](#failure-first-design)
- [Stable Work Identity](#stable-work-identity)
- [State Machines](#state-machines)
- [Recovery Ownership](#recovery-ownership)
- [Graceful Degradation](#graceful-degradation)
- [Verification](#verification)
- [See Also](#see-also)

## Purpose

Use this reference when a coding task changes runtime behavior and you need to decide which edge cases deserve application-level protection.

The standard is not "the app never fails." The standard is:

- Failures become explicit states.
- Duplicate work does not create duplicate side effects.
- Transient failures recover without a developer editing data by hand.
- Exhausted automation produces enough signal for a solo maintainer to act quickly.

## Failure-First Design

Before coding the happy path, write a compact failure map:

| Failure | Default design question |
|---|---|
| Duplicate input | How does the system recognize the same user intent again? |
| Concurrent input | What prevents two workers from owning the same resource? |
| Slow dependency | Where is the timeout and what state is recorded? |
| Transient dependency failure | Which errors retry, how often, and with what backoff? |
| Permanent dependency failure | What becomes terminal and what can the user do next? |
| Worker crash or deploy restart | What persisted state lets another worker resume safely? |
| Partial side effect | How do we reconcile, compensate, or make the next attempt safe? |
| Stale state | Who detects it, when, and what transition is allowed? |
| Load spike | What queues, caps, rate limits, or degraded paths protect the app? |
| Missing observability | Which log, metric, or trace answers "what happened to this work item?" |

Keep this map proportional. A low-risk admin label change needs a short pass. A payment, queue, import, webhook, or email flow needs a serious one.

## Stable Work Identity

Every side-effecting operation needs a durable identity. Examples:

- `idempotency_key` for API requests and form submissions.
- `webhook_event_id` for provider event delivery.
- `job_key` for coalescing duplicate background work.
- `message_id` plus `consumer_name` for inbox deduplication.
- Provider-level idempotency keys for payment, email, and provisioning APIs when supported.

Prefer caller-provided or domain-derived intent keys over hashes of the full payload. Two identical payloads can be two separate intents, and two slightly different payloads can be one retried intent with harmless metadata changes.

Store enough response or terminal state to answer a replay consistently. If the first attempt succeeded but the response was lost, the second attempt should not force the caller into a confusing "already exists" branch unless that is the explicit contract.

## State Machines

Use typed states for non-trivial work. Avoid free-form status strings scattered through handlers.

```ts
type WorkStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "canceled"
  | "stale";

type WorkRecord = {
  id: string;
  workKey: string;
  status: WorkStatus;
  attempt: number;
  maxAttempts: number;
  leaseOwner: string | null;
  leaseExpiresAt: Date | null;
  nextRunAt: Date | null;
  lastHeartbeatAt: Date | null;
  lastErrorCode: string | null;
};
```

Define allowed transitions:

| From | To | Owner |
|---|---|---|
| `pending` | `running` | worker that acquired the lease |
| `running` | `succeeded` | owning worker after durable side effect completes |
| `running` | `failed` | owning worker after terminal error or exhausted retries |
| `running` | `stale` | watchdog after heartbeat or lease expiry |
| `stale` | `pending` | watchdog or reconciler when retry is safe |
| `pending` | `canceled` | user/admin/system cancellation path |

Every non-terminal state needs:

- A timeout or expiration.
- A single owner or lease rule.
- A retry or terminal transition.
- Observability around entry, exit, and stale detection.

## Recovery Ownership

Pick the smallest mechanism that can reliably recover the failure:

| Failure | Likely owner |
|---|---|
| Duplicate HTTP submit | request handler plus database uniqueness or idempotency table |
| Duplicate webhook | webhook inbox table keyed by provider event ID |
| Worker crash | queue visibility timeout, lease expiry, or job heartbeat watchdog |
| Partial event publishing | transactional outbox and idempotent consumers |
| Provider timeout after unknown side effect | provider idempotency key plus reconciliation lookup |
| Cross-service business rollback | saga with explicit compensating actions |
| Load spike | queue-based load leveling, worker caps, rate limits, or degraded response |
| Poison message | dead-letter queue with inspection and controlled redrive |

Avoid recovery paths that require direct database surgery. If manual intervention is unavoidable, create an explicit admin command, script, or runbook that validates preconditions.

## Graceful Degradation

Graceful degradation is a product decision as much as an engineering pattern. Decide what the app should preserve when dependencies fail:

- Core action: accept the order, save the draft, let the user sign in, or show existing data.
- Optional action: defer email, delay analytics, hide recommendations, queue image processing, or show cached data.
- Unsafe action: block payment capture, permission changes, irreversible deletes, or compliance-sensitive exports when state is uncertain.

Use risk-based defaults:

- Fail closed for money, permissions, privacy, destructive actions, and legal obligations.
- Fail soft for notifications, recommendations, analytics, enrichment, previews, and non-critical decoration.
- Fail clearly for user-visible workflows: show status, retry affordance, and realistic next step.

## Verification

For meaningful app changes, verify at least one failure path:

- Duplicate request returns existing result instead of creating another record.
- Concurrent workers do not process the same work key.
- Timeout transitions work to retryable or failed state.
- Retry uses bounded backoff and preserves idempotency key.
- Stale work is detected and retried or made terminal.
- Logs include correlation ID and work identity.
- Metrics expose queue age, errors, retries, or saturation.

When local verification is not practical, state the gap and add the smallest hook that makes it testable next time.

## See Also

- `jobs-and-queues.md`
- `distributed-systems.md`
- `observability.md`
- `gotchas.md`
