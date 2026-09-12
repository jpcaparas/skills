# Naming And Intent

## Table of Contents

- [Name The Rule](#name-the-rule)
- [Strong Test Names](#strong-test-names)
- [Weak Names To Repair](#weak-names-to-repair)
- [Datasets And Parameterized Cases](#datasets-and-parameterized-cases)
- [Comments As Rationale](#comments-as-rationale)

---

## Name The Rule

Name tests after the behavior a user, domain expert, or maintainer cares about.

Prefer:

- `rejects withdrawals that exceed the current balance`
- `keeps the original balance when a withdrawal is rejected`
- `sends one receipt after a successful card payment`
- `preserves legacy rounding for invoices created before the tax migration`

Avoid:

- `testWithdraw`
- `works`
- `handles error`
- `returns false`
- `calls repository`

If the name cannot be written without mentioning private methods or helper classes, the test is probably coupled to implementation instead of behavior.

## Strong Test Names

Good names usually include:

- Trigger: the condition or action.
- Outcome: the expected result.
- Domain vocabulary: the terms production people use.

Patterns that travel across languages:

```php
it('rejects withdrawals that exceed the current balance', function () {
    // ...
});
```

```ts
it("expires invitations after the configured lifetime", () => {
  // ...
});
```

```py
def test_invoice_total_excludes_voided_line_items():
    ...
```

```go
func TestCheckoutRejectsExpiredCoupons(t *testing.T) {
    ...
}
```

## Weak Names To Repair

| Weak name | Problem | Better direction |
|---|---|---|
| `works` | Says nothing about behavior | `creates a paid invoice after a successful card charge` |
| `handles invalid input` | Hides the boundary | `rejects empty email addresses before sending invitations` |
| `returns false` | Names a mechanism | `rejects expired reset tokens` |
| `calls gateway` | Interaction is likely incidental | `charges the saved card once for the invoice balance` |
| `testLegacyCase` | Freezes mystery | `preserves legacy rounding for invoices created before 2025 tax migration` |

## Datasets And Parameterized Cases

Parameterized tests are maintainable when each case has a name that explains why the row exists.

Prefer:

```php
it('rejects invalid withdrawal amounts', function (Money $amount, string $reason) {
    $account = Account::openWithBalance(Money::nzd(5));

    $result = $account->withdraw($amount);

    expect($result)->toBeRejected()
        ->reason->toBe($reason);
})->with([
    'zero amount is not a withdrawal' => [Money::nzd(0), 'amount_must_be_positive'],
    'negative amount would credit the account' => [Money::nzd(-1), 'amount_must_be_positive'],
    'amount beyond balance has insufficient funds' => [Money::nzd(6), 'insufficient_funds'],
]);
```

Avoid anonymous tables where the reader has to infer the meaning from values alone.

## Comments As Rationale

Most tests should not need comments because the name and data explain the behavior. Add a short comment when it preserves context the code cannot express:

```php
it('preserves legacy rounding for invoices created before the tax migration', function () {
    // Customers were billed with half-up rounding before the 2025-04 tax migration.
    // Keep this until all pre-migration invoices are archived.
});
```

Use comments for:

- Legacy compatibility.
- Bug references.
- Regulatory or contractual behavior.
- Non-obvious edge cases.
- Temporary characterization before a refactor.

Do not use comments to restate the code line by line.

## See Also

- `references/legacy-and-characterization.md`
- `references/structure-and-fixtures.md`
