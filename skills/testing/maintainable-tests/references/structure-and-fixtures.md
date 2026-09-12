# Structure And Fixtures

## Table of Contents

- [Arrange Act Assert](#arrange-act-assert)
- [Keep Setup Close](#keep-setup-close)
- [Fixture Patterns](#fixture-patterns)
- [Assertion Quality](#assertion-quality)
- [Edge Case Coverage](#edge-case-coverage)
- [Top-Heavy Tests](#top-heavy-tests)

---

## Arrange Act Assert

Use Arrange / Act / Assert when it makes the behavior easier to scan. You do not always need literal comments, but the phases should be visible.

```php
it('allows withdrawing the available balance', function () {
    $account = Account::openWithBalance(Money::nzd(5));

    $result = $account->withdraw(Money::nzd(5));

    expect($result)->toBeOk();
    expect($account->balance())->toEqual(Money::nzd(0));
});
```

Add phase comments only when the setup is dense or the framework convention benefits from them:

```php
// Arrange
$account = Account::openWithBalance(Money::nzd(5));

// Act
$result = $account->withdraw(Money::nzd(6));

// Assert
expect($result)->toBeRejected();
```

## Keep Setup Close

The setup should expose the facts that matter to the behavior:

- Starting balance.
- Role or permission.
- Current date.
- Feature flag.
- Existing database row.
- External service response.

Hide incidental construction, not domain facts. A factory like `Account::openWithBalance(Money::nzd(5))` is useful because it keeps the key state visible. A factory like `makeFixture("case-42")` is not useful unless the case name is part of a documented catalogue.

## Fixture Patterns

Use the lightest fixture pattern that keeps the story readable:

| Pattern | Use when | Watch for |
|---|---|---|
| Inline setup | One or two domain facts define the scenario | Repetition is fine when it keeps examples clear |
| Test data builder | Many optional fields exist but each test names the important ones | Builder defaults must stay unsurprising |
| Factory | Framework/database setup has incidental boilerplate | Factory names should describe domain state |
| Object mother | A small set of canonical domain examples exists | Avoid becoming a dumping ground |
| Shared fixture | Expensive setup truly belongs to every test | Hidden coupling and order dependence |

## Assertion Quality

Prefer assertions that explain the expected observable result:

```php
expect($result)->toBeRejected()
    ->reason->toBe('insufficient_funds');
expect($account->balance())->toEqual(Money::nzd(5));
```

Avoid weak assertions that can pass while the behavior is wrong:

```php
expect($result)->toBeTruthy();
$this->assertNotNull($response);
```

Weak assertions are acceptable only as one part of a more specific proof.

Audit the assertion subject as carefully as the matcher. Confirm that the subject has the expected type and names the exact artifact, path, key, or collaborator used by production. A negated comparison between a boolean existence check and old file contents is trivially true; checking that the wrong backup path is absent proves nothing about the real backup.

For file-producing behavior, read the destination and compare its bytes or parsed value. Pair that with existence only when existence is itself part of the contract.

## Edge Case Coverage

Edge cases should be named and motivated. Good boundary tests teach why the boundary exists:

- `rejects zero-value withdrawals because they do not change account state`
- `allows withdrawing exactly the available balance`
- `rejects withdrawals one cent beyond the overdraft limit`
- `treats invitations as expired at the first second after the deadline`

Do not collapse unrelated boundaries into one large table. If a reader needs different domain explanations for each row, split the tests or name each dataset case clearly.

## Top-Heavy Tests

Symptoms:

- The first assertion appears after a page of setup.
- A `beforeEach` creates objects only some tests need.
- The test calls helpers whose names describe plumbing instead of behavior.
- A small policy needs a full framework boot, database, queue, and HTTP server.

Repairs:

- Move policy into a deterministic unit and test it directly.
- Keep adapter or framework integration tests for wiring.
- Replace broad shared setup with local builders.
- Use named factory states instead of mysterious defaults.
- Delete fixture fields that do not affect the assertion.

## See Also

- `references/doubles-and-boundaries.md`
- `references/side-effects-and-compatibility.md`
- `references/gotchas.md`
