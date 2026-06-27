# Maintainable Test Gotchas

## Table of Contents

- [Readable Is Not Always DRY](#readable-is-not-always-dry)
- [Test Helpers Can Become A Second Language](#test-helpers-can-become-a-second-language)
- [Mocks Can Freeze The Wrong Contract](#mocks-can-freeze-the-wrong-contract)
- [Snapshots Are Not Documentation By Themselves](#snapshots-are-not-documentation-by-themselves)
- [Parameterized Tests Need Case Names](#parameterized-tests-need-case-names)
- [Flaky Tests Destroy Trust](#flaky-tests-destroy-trust)
- [Coverage Metrics Can Distract](#coverage-metrics-can-distract)
- [Legacy Behavior Needs A Label](#legacy-behavior-needs-a-label)

---

## Readable Is Not Always DRY

Removing every repeated line can make tests harder to understand. In tests, a little duplication can keep each scenario readable in isolation.

Repair by extracting only incidental setup. Keep domain facts visible in the test.

## Test Helpers Can Become A Second Language

Helpers like `makeUser()` and `givenPaidInvoice()` can be helpful. Helpers like `setupCase(3)` or `createFixtureWithFlags()` force the reader to learn an undocumented mini-framework.

Repair by renaming helpers after domain states and deleting parameters that do not matter to the test.

## Mocks Can Freeze The Wrong Contract

Interaction tests are brittle when they pin private sequencing, helper calls, or implementation decomposition.

Repair by asserting observable behavior. Keep interaction assertions for effects that are genuinely part of the contract: gateway charge, email queued, event emitted, request serialized.

## Snapshots Are Not Documentation By Themselves

Snapshots can catch broad output drift, but large snapshots rarely explain intent. They are especially weak when the review surface is a blob of markup or JSON with many unrelated changes.

Repair by adding targeted assertions for the behavior the snapshot is meant to protect. Keep snapshots small and named after the scenario.

## Parameterized Tests Need Case Names

Anonymous rows make edge cases look arbitrary.

Repair by naming each case with the boundary or reason:

- `exact balance is allowed`
- `one cent beyond balance is rejected`
- `zero amount is not a withdrawal`

## Flaky Tests Destroy Trust

Tests that depend on real time, sleeps, random data, external services, local timezone, shared order, or concurrent timing become maintenance debt.

Repair by injecting clocks, seeding randomness, using local fakes, isolating persistence, and asserting eventual behavior with deterministic synchronization.

## Coverage Metrics Can Distract

Coverage tells you code ran. It does not prove the behavior is documented or meaningfully asserted.

Repair by reviewing tests against behavior risk: core rules, edge cases, failure modes, adapters, and legacy contracts.

## Legacy Behavior Needs A Label

A test that pins strange behavior without context makes the behavior look intentional forever.

Repair by adding a compact reason: compatibility, migration, customer data, incident, issue link, or temporary unknown with an owner.

## See Also

- `references/legacy-and-characterization.md`
- `references/review-rubric.md`
