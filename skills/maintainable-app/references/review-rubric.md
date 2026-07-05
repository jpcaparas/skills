# Resilience Review Rubric

## Table of Contents

- [Review Stance](#review-stance)
- [Severity](#severity)
- [Checklist](#checklist)
- [Common Findings](#common-findings)
- [See Also](#see-also)

## Review Stance

Use this rubric when reviewing code, plans, or diffs that affect application runtime behavior. Lead with concrete risks that could cause duplicate side effects, stuck work, silent failures, overload, data inconsistency, or unnecessary developer intervention.

## Severity

| Severity | Use when |
|---|---|
| Critical | The change can duplicate money/security/destructive side effects, lose user data, or make recovery require unsafe manual data edits |
| High | The change can create stuck jobs, unbounded retry storms, queue exhaustion, provider overload, or silent terminal failure |
| Medium | The change misses observability, degradation, bounded concurrency, stale detection, or focused failure-path tests |
| Low | The change has unclear naming, incomplete comments, weak runbook details, or non-blocking telemetry polish issues |

## Checklist

Ask these questions before approving:

- What happens if the same request arrives twice?
- What happens if ten users trigger the same expensive work at once?
- What happens if the worker crashes after the side effect but before status update?
- What happens if the provider times out after doing the work?
- What happens if the queue redelivers the message?
- What happens if the lock expires while the job is still running?
- What happens if `pending` or `running` lasts an hour?
- What happens if retries keep hitting an overloaded dependency?
- What happens if optional dependencies fail?
- What can the maintainer see without attaching a debugger?
- Which alert tells a human automation is exhausted?
- Which test proves the most likely failure mode?

## Common Findings

### Critical

- Side-effecting operation retries without idempotency key, unique constraint, or provider idempotency support.
- Payment, permission, destructive, or privacy-sensitive workflow fails open when state is uncertain.
- Event publishing and database writes are split without an outbox or reconciliation path.

### High

- Job has no stable work key, so concurrent requests enqueue duplicate expensive work.
- Worker timeout is longer than queue visibility or retry window, allowing duplicate processing.
- `pending` or `running` state has no expiration, heartbeat, watchdog, or terminal transition.
- Retry loop has no cap, no jitter, or retries at multiple layers.
- Dead-letter queue exists but has no alarm, inspection data, or redrive policy.

### Medium

- Logs omit correlation ID, work key, attempt count, dependency, or outcome.
- Metrics cannot show queue age, stale work, retries, dead letters, or saturation.
- Trace instrumentation misses the async handoff or external dependency where latency/failure occurs.
- Graceful degradation is mentioned but not implemented in code paths.
- Tests cover the happy path but not duplicate input, retry, timeout, stale state, or provider failure.

### Low

- Recovery comments explain mechanics but not why the retry or compensation is safe.
- Error class names hide whether an error is retryable, terminal, or requires reconciliation.
- Runbook says "retry manually" without naming the safe command or preconditions.

## See Also

- `principles.md`
- `jobs-and-queues.md`
- `distributed-systems.md`
- `observability.md`
- `gotchas.md`
