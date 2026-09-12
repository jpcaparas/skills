# Test Doubles

Use this reference when deciding how to replace a dependency in tests.

## Quick Choice

| Double | Use when | Avoid when |
|---|---|---|
| Stub | The dependency only needs to return fixed data or errors | Behavior is stateful or the call contract is the point |
| Fake | The dependency has meaningful state but can be implemented in memory | The fake would reimplement the real system poorly |
| Spy | The test needs to observe calls while still using simple behavior | Observations become more important than outcomes |
| Mock | The interaction itself is the contract, such as publishing one exact event | The test can assert observable behavior instead |
| Contract test | An adapter must keep matching an external service, SDK, schema, or protocol | The dependency is purely internal and covered elsewhere |

## Default Preference

Prefer stubs and fakes for most application behavior. They keep tests focused on outcomes and make refactors less brittle. Use mocks and spies where the interaction is the product behavior: sending an email, publishing an event, charging once, writing an audit record, or honoring retry/backoff rules.

## Contract Coverage

When production code depends on an adapter, add at least one check that protects the adapter boundary:

- Schema validation against real or recorded responses.
- Local integration test with a test container, emulator, or fixture server.
- Consumer-driven contract test if the provider is owned by another team.
- Thin smoke test for SDK wiring when no emulator exists.

Do not rely only on unit tests with mocks when the adapter translation is high risk.

## Fragile Test Smells

Inspect tests that:

- Mock private helpers or internal call order.
- Chain many mocks to set up one behavior.
- Assert exact calls that do not matter to users or contracts.
- Share mutable fake state across unrelated tests.
- Sleep to wait for time instead of controlling the scheduler.
- Hit shared external services for ordinary behavior tests.

## Practical Naming

Use names that reveal intent:

- `FixedClock`, `TestClock`, or `ManualScheduler`
- `InMemoryUserRepository`
- `CapturingEmailSender`
- `FailingPaymentGateway`
- `StubInventoryClient`
- `SpyEventPublisher`

Avoid vague names like `MockHelper`, `FakeService`, or `TestManager` when a domain-specific name is available.

## See Also

- `boundaries.md` for where to inject the double.
- `review-rubric.md` for severity ordering in reviews.
