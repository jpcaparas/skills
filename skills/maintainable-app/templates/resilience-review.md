# Application Resilience Review

## Scope

- Feature or workflow:
- User-visible promise:
- Durable state touched:
- External dependencies:
- Background work:

## Failure Map

| Failure mode | Current behavior | Desired failsafe | Owner |
|---|---|---|---|
| Duplicate input | | | |
| Concurrent input | | | |
| Dependency timeout | | | |
| Retryable provider error | | | |
| Worker crash or deploy restart | | | |
| Partial side effect | | | |
| Stale pending/running state | | | |
| Load spike | | | |

## Recovery Design

- Idempotency or work key:
- Concurrency control:
- Timeout and lease policy:
- Retry and backoff policy:
- Stale-work recovery:
- Dead-letter or terminal state:
- Reconciliation or compensation:
- Graceful degradation:

## Observability

- Logs:
- Metrics:
- Traces:
- Alerts:
- Dashboard or runbook:

## Verification

- Duplicate input:
- Retry:
- Timeout:
- Stale state:
- Dependency failure:
- Remaining gap:
