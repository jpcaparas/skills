# Legacy And Characterization Tests

## Table of Contents

- [When To Characterize](#when-to-characterize)
- [Writing Characterization Tests](#writing-characterization-tests)
- [Regression Tests](#regression-tests)
- [Documenting Legacy Rationale](#documenting-legacy-rationale)
- [Changing Behavior Safely](#changing-behavior-safely)

---

## When To Characterize

Add characterization tests before refactoring code whose behavior is important but poorly understood. The goal is to capture what the system currently does so you can change structure without accidentally changing behavior.

Good candidates:

- Legacy billing, permissions, tax, migration, or compatibility rules.
- Code with no reliable tests but high production risk.
- Branches whose behavior is known only from incidents or customer data.
- Adapters where external protocol assumptions are implicit.

Do not over-characterize noise. Capture behaviors that matter to users, data, contracts, or operations.

## Writing Characterization Tests

Make uncertainty explicit:

```php
it('preserves current invoice rounding before refactoring tax calculation', function () {
    // Characterization: this records existing behavior before decomposing TaxCalculator.
    // Replace with principled tax examples after the migration rule is clarified.
    $invoice = Invoice::legacyDraft(total: Money::nzd(10.005));

    $tax = $invoice->calculateTax();

    expect($tax)->toEqual(Money::nzd(1.50));
});
```

This tells the reader the test is temporary evidence, not a timeless product rule.

## Regression Tests

Regression tests should fail for the bug they guard against. Include the condition that caused the bug and the corrected outcome.

Good regression names:

- `keeps the account balance unchanged after a rejected withdrawal`
- `does not send duplicate receipts when the gateway retry succeeds`
- `preserves archived invoice totals during the currency migration`

When useful, include a compact issue reference:

```php
it('does not resend receipts after retrying a paid invoice', function () {
    // Regression for BILL-842: gateway retries can return the original success response.
});
```

## Documenting Legacy Rationale

Legacy tests need one of these rationales:

- Contractual: a customer, API, or data format depends on this behavior.
- Historical: existing stored data was produced this way.
- Migration: behavior is pinned until a named migration completes.
- Regulatory: law, policy, or audit rules require this shape.
- Unknown: current behavior is recorded temporarily while the team investigates.

Unknown is acceptable during characterization. It is not acceptable as permanent documentation without an owner or follow-up.

## Changing Behavior Safely

1. Add characterization tests around current behavior.
2. Refactor production code without changing those tests.
3. Add new behavior tests for the desired rule.
4. Change production behavior.
5. Delete or rewrite characterization tests that no longer describe intended behavior.
6. Keep regression tests that document bugs likely to recur.

Do not leave both old and new expectations in the suite unless the system intentionally supports both modes.

## See Also

- `references/naming-and-intent.md`
- `references/review-rubric.md`
