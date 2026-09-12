# Source Notes

## Table of Contents

- [Purpose](#purpose)
- [Sources Used](#sources-used)
- [Adaptation Notes](#adaptation-notes)
- [See Also](#see-also)

## Purpose

This skill adapts durable distributed-systems, queueing, and observability guidance into agent instructions for application coding tasks. It avoids copying provider-specific details into generic rules when the behavior depends on a framework or platform.

## Sources Used

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

## Adaptation Notes

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

## See Also

- `principles.md`
- `jobs-and-queues.md`
- `distributed-systems.md`
- `observability.md`
