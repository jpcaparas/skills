# Source Notes

This skill adapts stable maintainability ideas into agent behavior. It does not copy any source as a rulebook.

## Influences

- nunomaduro/essentials: Treat strictness, immutability, environment-scoped safety, compatibility checks, and repository automation as executable defaults rather than review folklore. The dissection was pinned to commit `bad47a6653a035ef8033856f0c4af3b65a704293` from 2026-05-14.
- shadcn/improve: Treat planning as a product. Do recon first, verify evidence, and write self-contained plans for executors that lack session context.
- Martin Fowler's refactoring guidance: Prefer small behavior-preserving transformations and use tests to reduce risk while improving design.
- Google Engineering Practices: Optimize code review for improving code health over time, not for perfection or personal taste.
- Cognitive complexity work from SonarSource: Understandability is distinct from testability; deeply nested or mentally expensive code deserves refactoring even when branch coverage looks adequate.
- Clean Code ideas associated with Robert C. Martin: Names, functions, comments, and boundaries matter, but apply them pragmatically rather than as slogans.
- Operational engineering practice from CI/CD, shell, infrastructure, and migration work: dense glue code needs context comments because syntax alone rarely exposes external contracts, failure modes, or artifact/data-shape assumptions.

## Adaptation Choices

This skill intentionally avoids absolute rules like "never comment" or "every function must be tiny." Those rules are easy for agents to over-apply and often make code worse. It treats comments as maintainability tools when names, types, and structure cannot carry system context by themselves.

The Essentials adaptation is selective. It generalizes the repository's layered strictness, narrow configurable lifecycle, safe destructive-operation defaults, compatibility seams, lowest-supported dependency checks, and check-mode automation. It does not canonize framework-specific choices such as public class-name configuration keys, side-effectful collection pipelines, an action class for every operation, unconditional transactions, or repetitive docblocks.

Instead, it uses maintainability gates:

- Can a human understand the intent?
- Is behavior preserved?
- Are responsibilities stable?
- Is verification proportional to risk?
- Does the code fit the repository?

## Pinned Essentials Evidence

| Evidence | Adapted lesson | Caveat retained here |
|---|---|---|
| `Configurable.php` and `EssentialsServiceProvider.php` | A typed registry can separate policy selection from application when several optional startup policies share a lifecycle | Prefer a direct loop when a fluent pipeline hides dependency resolution, order, or effects |
| `ShouldBeStrict.php`, `ImmutableDates.php`, `phpstan.neon.dist`, and `pint.json` | Layer language, analyzer, formatter, and framework strictness; make value-like state immutable | Treat runtime strictness as a behavior migration in established systems |
| `ProhibitDestructiveCommands.php` plus the publish commands | Default dangerous behavior off and give overwrites confirmation, an explicit automation path, and recovery | A force flag never bypasses authorization, validation, invariants, or promised backup verification |
| `AutomaticallyEagerLoadRelationships.php`, `composer.json`, and `tests.yml` | Use the stack's compatibility seam and test lowest/current supported combinations; this source demonstrates runtime feature detection | Required capabilities must fail with context rather than silently no-op |
| Composer scripts and both GitHub Actions workflows | Compose formatter check mode, static analysis, refactor dry-runs, tests, pinned automation, and least permissions | Automated refactors still need diff review and behavior verification |

All lessons above are paraphrased from the MIT-licensed source and checked against the pinned snapshot; no upstream implementation is copied into this skill.

## Resilience, Queueing, And Observability Sources

The resilience guidance adapts durable distributed-systems, queueing, and observability guidance into agent instructions for application coding tasks. It avoids copying provider-specific details into generic rules when the behavior depends on a framework or platform:

- AWS Builders' Library, "Timeouts, retries, and backoff with jitter": https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
- AWS Builders' Library, "Making retries safe with idempotent APIs": https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
- Google SRE Book, "Monitoring Distributed Systems": https://sre.google/sre-book/monitoring-distributed-systems/
- Microsoft Azure Architecture Center, "Cloud Design Patterns": https://learn.microsoft.com/en-us/azure/architecture/patterns/
- Microsoft Azure Architecture Center, "Queue-Based Load Leveling pattern": https://learn.microsoft.com/en-us/azure/architecture/patterns/queue-based-load-leveling
- Microsoft Azure Architecture Center, "Competing Consumers pattern": https://learn.microsoft.com/en-us/azure/architecture/patterns/competing-consumers
- Microsoft Azure Architecture Center, "Bulkhead pattern": https://learn.microsoft.com/en-us/azure/architecture/patterns/bulkhead
- Google Cloud Architecture Center, "Design for graceful degradation": https://docs.cloud.google.com/architecture/framework/reliability/graceful-degradation
- OpenTelemetry, "Semantic Conventions": https://opentelemetry.io/docs/concepts/semantic-conventions/
- Laravel Queues documentation: https://laravel.com/docs/13.x/queues
- Stripe API Reference, "Idempotent requests": https://docs.stripe.com/api/idempotent_requests
- Amazon SQS Developer Guide, "Using dead-letter queues": https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html
- Microservices.io, "Transactional outbox": https://microservices.io/patterns/data/transactional-outbox.html
- Microservices.io, "Saga": https://microservices.io/patterns/data/saga.html

Adaptation notes:

- AWS guidance on retries, backoff, jitter, and idempotent APIs informs the default retry policy, idempotency-key guidance, and warning against retry amplification.
- Google SRE's golden signals inform the metrics baseline: latency, traffic, errors, and saturation.
- Azure queue and consumer patterns inform queue-based load leveling, competing consumers, and pairing retries with circuit breakers or isolation.
- Azure bulkhead guidance informs the recommendation to isolate resources by queue, worker pool, tenant, dependency, or feature class.
- Google Cloud graceful degradation guidance informs fail-soft behavior for optional features and early load shedding during overload.
- OpenTelemetry semantic conventions inform the recommendation to use shared names for traces, metrics, logs, profiles, and resources when OTel exists in the codebase.
- Laravel queue documentation informs the practical warnings about unique jobs, overlap locks, attempts, worker timeouts, and retry-after or visibility timing.
- Stripe idempotency docs inform the guidance to persist idempotency keys, reuse keys for retries, avoid sensitive keys, and reject materially different parameters for the same key.
- SQS dead-letter queue documentation informs the DLQ checklist, max receive count guidance, retention warning, and note that FIFO ordering can be affected.
- Transactional outbox and saga patterns inform the outbox/inbox, idempotent consumer, and compensating-transaction guidance.

## Testability And Dependency Sources

The testability guidance distills widely used testing and design practices into agent instructions:

- Hexagonal architecture and ports/adapters for isolating external systems.
- Dependency inversion as a boundary tool, not an interface quota.
- Test double vocabulary from common testing literature: dummy, stub, fake, spy, mock.
- Functional core, imperative shell for deterministic business behavior.
- Contract and integration tests as a backstop for mocked adapters.
- Framework-native override patterns such as fixtures, providers, contexts, and test containers.

The instructions are intentionally language agnostic. Prefer the local codebase's idioms over importing a pattern mechanically.

## Source URLs

- `https://github.com/nunomaduro/essentials/tree/bad47a6653a035ef8033856f0c4af3b65a704293`
- `https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/src/Contracts/Configurable.php`
- `https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/src/EssentialsServiceProvider.php`
- `https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/composer.json`
- `https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/.github/workflows/tests.yml`
- `https://github.com/nunomaduro/essentials/blob/bad47a6653a035ef8033856f0c4af3b65a704293/LICENSE.md`
- `https://github.com/shadcn/improve`
- `https://raw.githubusercontent.com/shadcn/improve/main/skills/improve/SKILL.md`
- `https://martinfowler.com/books/refactoring.html`
- `https://martinfowler.com/bliki/CodeSmell.html`
- `https://google.github.io/eng-practices/review/reviewer/standard.html`
- `https://www.sonarsource.com/resources/cognitive-complexity/`
- `https://www.sonarsource.com/blog/cognitive-complexity-because-testability-understandability`
- `https://www.php.net/manual/en/language.basic-syntax.comments.php`
- `https://docs.python.org/3/tutorial/controlflow.html#documentation-strings`
- `https://laravel.com/docs/13.x/eloquent-mutators`
- `https://laravel.com/docs/13.x/routing`
- `https://nextjs.org/docs/app/api-reference/file-conventions/route`
- `https://nextjs.org/docs/app/getting-started/fetching-data`

## See Also

- `references/principles.md`
- `references/commenting.md`
- `references/guardrails-and-quality-gates.md`
