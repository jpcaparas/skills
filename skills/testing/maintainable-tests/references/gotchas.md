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
- [Plausible Assertions Can Be False Positives](#plausible-assertions-can-be-false-positives)
- [Current-Only CI Overstates Compatibility](#current-only-ci-overstates-compatibility)

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

## Plausible Assertions Can Be False Positives

A matcher can look specific while inspecting the wrong subject. Comparing a file-existence boolean with old file contents, or checking a typoed backup path, will stay green even when the protected write behavior is wrong.

Repair by tracing the production effect to its exact path and value type. Assert the before/after contents, backup bytes, or emitted value that would change if the behavior regressed.

## Current-Only CI Overstates Compatibility

Testing only the newest runtime or dependency version leaves the advertised lower bound unproved. Optional APIs can also disappear behind broad version skips.

Repair by testing the lowest supported combination and current stable combinations. When production feature-detects or conditionally compiles an optional capability, also cover focused capability-present and capability-absent paths. Use narrow skip reasons that name the missing capability.

## See Also

- `references/legacy-and-characterization.md`
- `references/review-rubric.md`
- `references/side-effects-and-compatibility.md`
