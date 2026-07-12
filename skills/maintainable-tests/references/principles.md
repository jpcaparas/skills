# Maintainable Test Principles

## Table of Contents

- [Reader Contract](#reader-contract)
- [Behavior Before Implementation](#behavior-before-implementation)
- [Readable Beats Clever](#readable-beats-clever)
- [Coverage With Intent](#coverage-with-intent)
- [Balanced Test Portfolio](#balanced-test-portfolio)
- [Cross-Language Behavior Examples](#cross-language-behavior-examples)

---

## Reader Contract

Write tests for the next developer who understands the language but does not remember the product history. Good tests answer three questions quickly:

1. What behavior matters?
2. Which examples define the boundary?
3. Why does this behavior deserve a test?

The answer should come from names, data, setup, and assertions before the reader opens the production implementation.

## Behavior Before Implementation

Default to behavior-shaped tests:

```php
it('rejects withdrawals that exceed the current balance', function () {
    $account = Account::openWithBalance(Money::nzd(5));

    $result = $account->withdraw(Money::nzd(6));

    expect($result)->toBeRejected()
        ->reason->toBe('insufficient_funds');

    expect($account->balance())->toEqual(Money::nzd(5));
});
```

The test name, values, action, and assertions all teach the rule. A reader does not need to know the method internals to understand the business behavior.

Implementation-shaped tests are acceptable only when the implementation contract is the product surface: generated SQL, API request shape, telemetry emission, cache key compatibility, or adapter protocol.

## Readable Beats Clever

Tests have a different maintainability profile from production code. Production code often benefits from removing duplication; tests often benefit from preserving enough repetition that each scenario stands alone.

Use helpers when they reduce noise without hiding the behavior:

```php
$account = Account::openWithBalance(Money::nzd(5));
```

Avoid helpers that force the reader to decode policy:

```php
$subject = makeSubjectForCase('B7');
```

The helper name should carry domain meaning, not fixture machinery.

## Coverage With Intent

Every non-trivial test should have a reason:

- It documents a core domain rule.
- It protects a bug fix.
- It pins legacy compatibility until a migration is complete.
- It covers an edge case where failures are plausible or costly.
- It verifies an adapter contract that can drift.

Do not add tests only to raise a percentage. A high-coverage suite with vague names and weak assertions can still be expensive to maintain.

## Balanced Test Portfolio

Favor a portfolio that gives fast feedback and meaningful confidence:

- Unit or policy tests for deterministic rules.
- Contract tests for adapters and framework boundaries.
- Integration tests for wiring, persistence, serialization, and external protocol assumptions.
- A small number of end-to-end tests for critical user journeys.

The exact shape depends on the codebase. The test pyramid is a useful conversation starter, not a quota.

## Cross-Language Behavior Examples

Short behavior descriptions are portable across test frameworks. This Pest example demonstrates the shape without making its syntax a requirement:

```php
it('allows overdraft withdrawals within the configured limit', function () {
    $account = Account::openWithBalance(Money::nzd(5));
    $account->enableOverdraft(Money::nzd(1));

    $result = $account->withdraw(Money::nzd(6));

    expect($result)->toBeOk();
});
```

Carry the same behavior name, visible setup, action, and outcome into the project's own ecosystem:

```ts
it("allows overdraft withdrawals within the configured limit", () => {
  const account = Account.openWithBalance(Money.nzd(5));
  account.enableOverdraft(Money.nzd(1));

  const result = account.withdraw(Money.nzd(6));

  expect(result).toEqual(ok());
});
```

The framework matters less than the discipline: behavior name, minimal setup, one action, specific assertions.

## See Also

- `references/naming-and-intent.md`
- `references/structure-and-fixtures.md`
- `references/source-notes.md`
