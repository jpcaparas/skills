# Gotchas

Common ways maintainability guidance goes wrong.

## Over-Extraction

Small helpers help only when they name stable concepts. Extracting every branch into a tiny function can create a reading maze.

Repair:

- Keep simple local logic inline.
- Extract named domain concepts.
- Group private helpers near their caller when the language supports it.

## Premature Generality

A generic engine, registry, plugin layer, or rule system is usually more expensive than a few explicit functions until there is real variation.

Repair:

- Keep the first implementation direct.
- Note likely extension points without implementing them.
- Add abstraction when the second or third concrete case proves the axis of change.

## False DRY

Two blocks that look similar may change for different reasons. Merging them creates shared risk.

Repair:

- Ask what business rule owns each block.
- Share pure mechanical transformations.
- Keep policy duplicated until the shared reason to change is real.

## Clean-Code Cargo Culting

Rules like "functions should be tiny" or "comments are bad" are harmful when applied without context.

Repair:

- Prefer local evidence over slogans.
- Explain the maintainer risk.
- Use tests and reviewability as the judge.

## Comment Starvation

Agent-generated code often starts with clear high-level steps, then drops into dense command pipelines, workflow YAML, migrations, or generated glue with no explanation. It also tends to document only the class or file header while leaving method contracts, property units, and block-level invariants unexplained. This forces future maintainers to reverse-engineer the system from syntax.

Repair:

- Add phase comments before multi-step operational blocks.
- Add method, property, branch, and block comments where that smaller scope carries the real maintenance risk.
- Explain external API contracts, artifact names, cache keys, and failure-mode decisions.
- Write for a junior maintainer with good fundamentals but limited system context.

## Source-Less Claims

Framework and language comments become risky when they make claims without a source. A future maintainer cannot tell whether the note came from official documentation, a stale blog post, local convention, or an agent guess.

Repair:

- Link official docs when they exist and the claim affects correctness, maintainability, security, or upgrades.
- Verify the URL resolves before including it in reusable instructions or review notes.
- Paraphrase the official behavior and keep long explanations in the source, not in the code comment.
- If the claim comes from local evidence instead of docs, point to the file, test, or observed behavior.

## Diagram Drift

ASCII diagrams help when they make state, data flow, or ownership visible. They become harmful when the code changes and the diagram still describes the old branch, queue, retry path, or data shape.

Repair:

- Add diagrams only for concepts that are hard to scan from prose and names alone.
- Keep diagram labels aligned with real functions, states, events, or domain terms.
- Review diagram arrows and surrounding prose together during edits.
- Update stale text and stale diagrams in the same change; do not let them contradict each other.

## Comment Noise

Comments that repeat syntax make useful comments easier to ignore.

Repair:

- Rename or restructure first when code can explain itself.
- Keep comments for why, invariants, tradeoffs, and surprising constraints.
- Remove stale comments when the code no longer matches them.

## Type Theater

Types that merely rename `string`, `any`, or generic records without constraining behavior can create false confidence.

Repair:

- Use types to encode states, units, variants, and required fields.
- Narrow at boundaries.
- Avoid casting away uncertainty before validation.

## Agent Style Drift

Agents often import habits from other ecosystems: new folder conventions, generic helpers, alternate test frameworks, and unnecessary dependencies.

Repair:

- Read nearby code before editing.
- Reuse existing helpers.
- Add dependencies only when they pay for themselves and fit the project.

## Hidden Error Collapse

Mapping every failure to `false`, `null`, or "Something went wrong" removes the context maintainers need.

Repair:

- Preserve original error context at logs or typed error causes.
- Convert errors at user-facing boundaries.
- Test important failure modes.

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

## Work State

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

## Mockability Traps

1. Interface inflation.
   Adding an interface for every class creates noise without improving substitution. Add contracts at dependency ownership boundaries or where a real fake, stub, or adapter exists.

2. Mocking the design instead of the behavior.
   A test that asserts every internal call usually freezes implementation. Assert outcomes unless call shape is the actual contract.

3. Production wiring with no coverage.
   Injected dependencies can make unit tests pass while the real application cannot construct the graph. Keep a smoke, integration, or contract test for wiring that matters.

4. Hidden deterministic dependencies.
   Clocks, random values, environment reads, locale, timezone, current user, and process-wide context can make tests flaky even without network or database calls.

5. Test-only APIs.
   Public setters, mutable globals, or flags added only for tests weaken production design. Prefer explicit construction, parameters, fixtures, or framework-supported overrides.

6. Over-faking external systems.
   An in-memory fake can drift from a database, broker, or external API. Use fakes for behavior speed, then backstop risky translation with contract or integration checks.

7. Monkeypatch dependency.
   Patching module globals is sometimes the least disruptive move in legacy code, but new core code should usually expose a clearer replacement point.

8. Async and scheduler leaks.
   Sleeps, real timers, background jobs, and unjoined tasks make tests slow or flaky. Prefer controllable schedulers, explicit await points, captured queues, or deterministic job runners.

9. Constructor work.
   Constructors that call networks, read files, start threads, or inspect environment are hard to replace and hard to fail safely. Move effects into explicit start/connect/load calls or outer wiring.

10. Vendor-shaped domain code.
    Passing vendor SDK objects deep into business logic couples tests to transport details. Translate at an adapter boundary into domain-shaped data where practical.

### Mockability Repair Heuristic

When a test cannot replace a dependency, ask:

1. Is the dependency needed for the behavior under test?
2. Who should own creating it in production?
3. What is the smallest contract the behavior needs?
4. What double would honestly model it?
5. What adapter or integration check prevents drift?

Stop once the current risk is verifiable. Do not keep abstracting after the dependency is replaceable and the production path remains clear.

## See Also

- `references/principles.md`
- `references/decomposition.md`
- `references/guardrails-and-quality-gates.md`
- `references/resilience.md`
- `references/jobs-and-queues.md`
- `references/distributed-systems.md`
- `references/observability.md`
- `references/dependency-boundaries.md`
- `references/test-doubles.md`
