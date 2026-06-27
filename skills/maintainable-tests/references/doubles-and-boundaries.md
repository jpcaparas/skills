# Doubles And Boundaries

## Table of Contents

- [Choose The Least Powerful Double](#choose-the-least-powerful-double)
- [When Interaction Is The Behavior](#when-interaction-is-the-behavior)
- [Design Feedback From Painful Tests](#design-feedback-from-painful-tests)
- [Refactor For Testability](#refactor-for-testability)
- [Contract And Integration Checks](#contract-and-integration-checks)

---

## Choose The Least Powerful Double

| Double | Use when | Avoid when |
|---|---|---|
| Stub | The collaborator only needs to return a canned answer | You need to model state changes |
| Fake | A small in-memory implementation better explains behavior | The fake becomes a second production system |
| Spy | You need to observe an important side effect | You are checking incidental call order |
| Mock | The interaction itself is the contract | You only care about final state or return value |
| Contract test | A fake or adapter can drift from the real dependency | The dependency is purely internal and already covered |

Prefer behavior assertions over interaction assertions when either would prove the same thing.

## When Interaction Is The Behavior

Mock or spy assertions are useful when the interaction is the observable promise:

- A payment gateway is charged exactly once.
- A transactional email is queued with a specific template and recipient.
- A domain event is published after state changes.
- An adapter sends a request matching an external API contract.

Keep the assertion focused on the contract. Do not pin every private method call that happens to occur along the way.

## Design Feedback From Painful Tests

Hard-to-write tests often reveal production design issues:

- Domain policy is tangled with framework handlers.
- Time, randomness, environment, or locale is read deep inside logic.
- External SDK clients are constructed inside the method under test.
- Private methods contain behavior that wants a name.
- One function both decides and performs irreversible effects.

Do not paper over these problems with reflection, sleeps, global monkeypatches, or excessive mocks. Improve the boundary when it makes both production code and tests easier to understand.

## Refactor For Testability

Good refactors for tests also improve production readability:

```ts
// Before: hard to test without real time and gateway construction.
export async function chargeInvoice(invoice: Invoice) {
  const gateway = new PaymentGateway(process.env.PAYMENT_KEY ?? "");
  return gateway.charge(invoice.total(), Date.now());
}
```

```ts
type Clock = { now(): number };
type PaymentPort = { charge(amount: Money, chargedAt: number): Promise<ChargeResult> };

export async function chargeInvoice(invoice: Invoice, payment: PaymentPort, clock: Clock) {
  return payment.charge(invoice.total(), clock.now());
}
```

The second shape names the dependencies. Tests can use a stub clock and fake payment port without changing production behavior.

Keep production wiring convenient:

```ts
export function makeInvoiceCharger(config: Config) {
  return (invoice: Invoice) =>
    chargeInvoice(invoice, new PaymentGateway(config.paymentKey), systemClock);
}
```

## Contract And Integration Checks

When tests use fakes or mocks for an external boundary, add a small contract or integration check where drift would be costly:

- Adapter serializes the request the external API expects.
- Repository fake and database repository share the same query semantics.
- Queue publisher emits the same event schema the consumer expects.
- HTTP handler still maps domain errors to status codes correctly.

This keeps fast tests readable without pretending every dependency is fully verified by mocks.

## See Also

- `references/structure-and-fixtures.md`
- `references/legacy-and-characterization.md`
