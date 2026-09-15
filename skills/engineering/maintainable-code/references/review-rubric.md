# Review Rubric

Use this for code review, self-review, or final diff inspection.

## Output Order

Lead with findings, ordered by maintainer impact:

1. Behavior or data correctness risk
2. Test gaps that make future change unsafe
3. Confusing ownership or boundaries
4. Over-generalized or under-named abstractions
5. Error handling and observability gaps
6. Missing developer context in dense operational, generated, or cross-boundary code
7. Local consistency, style, and nits

Do not lead with compliments or broad summaries. If there are no findings, say that clearly and mention residual risk.

## Finding Format

Each finding should include:

- Severity: P0, P1, P2, or P3
- File and line
- Concrete maintainer impact
- Why the current shape is risky
- A repair direction, not necessarily a full patch
- Whether tests should change

Example shape:

```text
[P2] Keep retry state out of the shared client singleton
src/api/client.ts:84
The retry counter is stored on the client instance, so concurrent requests can affect each other's retry budget. Keep retry state inside the request call and add a concurrency-focused regression test.
```

## Maintainability Smells

Treat these as leads to inspect, not automatic failures:

- A function mixes validation, I/O, policy, and presentation.
- A generic class replaces a small set of clear functions.
- New configuration accepts arbitrary strings or untyped dictionaries.
- A helper name describes mechanics instead of domain meaning.
- Tests assert implementation calls but not behavior.
- The change creates a second pattern beside an existing local pattern.
- A catch block drops context or converts all failures into the same error.
- A CI workflow, shell script, migration, generated file, or config block has dense command logic without comments explaining phases, invariants, or external contracts.
- A module named `utils`, `common`, or `helpers` becomes a dumping ground.

## Review Discipline

Technical facts beat preferences. If a design choice is merely different from your taste but consistent, tested, and understandable, do not block on it.

Use "nit" only for non-blocking polish. Do not disguise design concerns as nits.

When recommending extraction, name the boundary and why it will change independently. If you cannot do that, recommend renaming or local simplification instead.

## Self-Review Checklist

Before handing off a diff:

- Re-read the changed files without relying on session memory.
- Check that each new name carries domain meaning.
- Check that failure paths preserve useful context.
- Check that tests would fail before the fix or protect the new contract.
- Check that generated code did not introduce a parallel style.
- Check that comments teach non-obvious context instead of narrating syntax.
- Check that any TODO has an owner, reason, or follow-up path.

## Resilience Scope

Use this severity guide when the diff or plan affects application runtime behavior: background jobs, queues, webhooks, external providers, persistence transitions, or observability. Lead with concrete risks that could cause duplicate side effects, stuck work, silent failures, overload, data inconsistency, or unnecessary developer intervention.

| Severity | Use when |
|---|---|
| Critical | The change can duplicate money/security/destructive side effects, lose user data, or make recovery require unsafe manual data edits |
| High | The change can create stuck jobs, unbounded retry storms, queue exhaustion, provider overload, or silent terminal failure |
| Medium | The change misses observability, degradation, bounded concurrency, stale detection, or focused failure-path tests |
| Low | The change has unclear naming, incomplete comments, weak runbook details, or non-blocking telemetry polish issues |

### Resilience Checklist

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

### Common Resilience Findings

Critical:

- Side-effecting operation retries without idempotency key, unique constraint, or provider idempotency support.
- Payment, permission, destructive, or privacy-sensitive workflow fails open when state is uncertain.
- Event publishing and database writes are split without an outbox or reconciliation path.

High:

- Job has no stable work key, so concurrent requests enqueue duplicate expensive work.
- Worker timeout is longer than queue visibility or retry window, allowing duplicate processing.
- `pending` or `running` state has no expiration, heartbeat, watchdog, or terminal transition.
- Retry loop has no cap, no jitter, or retries at multiple layers.
- Dead-letter queue exists but has no alarm, inspection data, or redrive policy.

Medium:

- Logs omit correlation ID, work key, attempt count, dependency, or outcome.
- Metrics cannot show queue age, stale work, retries, dead letters, or saturation.
- Trace instrumentation misses the async handoff or external dependency where latency/failure occurs.
- Graceful degradation is mentioned but not implemented in code paths.
- Tests cover the happy path but not duplicate input, retry, timeout, stale state, or provider failure.

Low:

- Recovery comments explain mechanics but not why the retry or compensation is safe.
- Error class names hide whether an error is retryable, terminal, or requires reconciliation.
- Runbook says "retry manually" without naming the safe command or preconditions.

## Testability Scope

Use this severity guide when the change risks making behavior hard to isolate in tests. Lead with hidden side effects, hardcoded collaborators, brittle interaction tests, and missing contract coverage. Keep style preferences out unless they materially affect testability or future changes.

| Severity | Finding type | Why it matters |
|---|---|---|
| Critical | Tests must hit real payment, email, production database, destructive filesystem, or shared service for ordinary behavior | Failures can cost money, mutate real state, or block safe verification |
| High | Business policy is tangled with hardcoded network, database, clock, random, env, queue, or framework state | Important behavior cannot be tested deterministically or safely |
| High | Error, timeout, retry, or partial-failure behavior cannot be simulated | The riskiest paths remain unverified |
| Medium | A broad SDK/client/service is passed where a narrow contract would clarify ownership | Tests become coupled to vendor details and setup grows brittle |
| Medium | Tests overuse mocks for implementation details instead of observable behavior | Refactors break tests even when behavior is preserved |
| Medium | Production wiring is hidden behind globals, service locators, or implicit containers | Replacements are hard to reason about and integration failures hide |
| Low | Names like `MockService` or `Helper` obscure the role of a test double | Readability suffers but behavior may still be safe |

### Testability Finding Format

```markdown
## Findings

- Severity: file:line - Concrete mockability issue.
  Impact: What behavior cannot be isolated or what failure path cannot be simulated.
  Repair: Smallest practical boundary or test-double change.

## Open Questions

- Any dependency ownership or framework lifecycle uncertainty.

## Verification Notes

- Tests or checks run.
- Remaining real-service or contract-test gap.
```

### Testability Review Discipline

- Do not ask for dependency injection everywhere by default.
- Do not require interfaces for value objects, pure functions, or stable internal helpers.
- Do not convert every behavior test into interaction mocks.
- Do not ignore adapter or integration coverage once mocks are introduced.
- Do not recommend monkeypatching as the only long-term strategy for core code.

## See Also

- `references/decomposition.md`
- `references/commenting.md`
- `references/guardrails-and-quality-gates.md`
- `references/resilience.md`
- `references/jobs-and-queues.md`
- `references/dependency-boundaries.md`
- `references/test-doubles.md`
