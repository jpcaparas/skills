---
name: maintainable-tests
description: "Guide maintainable tests as behavior documentation with isolated side effects, compatibility coverage, and reliable assertions. Use for tests, fixtures, mocks, regressions, reviews, and testability changes. Skip disposable work."
compatibility: "No external dependencies. Optional helper scripts require python3."
metadata:
  version: "1.1.0"
  short-description: "Write tests that document behavior and stay humane to maintain"
  openclaw:
    category: "development"
    requires:
      bins: [python3]
references:
  - principles
  - naming-and-intent
  - structure-and-fixtures
  - doubles-and-boundaries
  - legacy-and-characterization
  - side-effects-and-compatibility
  - review-rubric
  - gotchas
  - source-notes
---

# maintainable-tests

Write, edit, refactor, and review tests so a developer returning months later can understand the behavior, the edge cases, and the reason each important test exists.

## Passive Trigger

Load this skill in the background whenever the task involves automated tests, examples used as tests, fixtures, mocks, stubs, fakes, test data builders, regression coverage, characterization tests, flaky tests, or production-code changes made to improve testability. Keep it lightweight for small edits: apply the core rules silently, then mention only the test-design decisions that affect the final implementation.

## Decision Tree

Consult the relevant reference only when a non-obvious test-design decision needs more detail than these rules or local examples provide. A matching topic does not require a reference read.

- Adding tests for new behavior:
  Name each test after the user-visible rule or domain invariant, then use concrete examples that teach the behavior. Consult `references/principles.md` or `references/naming-and-intent.md` if intent is unclear.

- Fixing a bug or adding regression coverage:
  Prove the broken scenario and expected behavior, reusing adequate coverage where it exists. Consult `references/legacy-and-characterization.md` when preserving legacy behavior or explaining uncertainty needs care.

- Covering edge cases:
  Keep the happy path visible, then cover meaningful boundaries without duplicating adequate tests. Consult `references/structure-and-fixtures.md` for difficult fixture or case organization.

- Tests are hard because the production code is tangled or unmockable:
  Use existing safe seams first, including framework overrides or scoped, reliably restored legacy patches. Refactor production only when necessary, proportionate, and authorized. Consult `references/doubles-and-boundaries.md`, or {{ skill:maintainable-code }} if available, when a boundary decision remains unresolved. In tests-only work, propose a needed production change rather than making it.

- Refactoring legacy code before changing behavior:
  Reuse adequate behavior coverage; add characterization only for important gaps. Label intentional legacy behavior and change production code in small verified steps. Consult `references/legacy-and-characterization.md` when the preservation contract is unclear.

- Reviewing a test diff:
  Lead with tests that can pass while behavior is broken, brittle implementation coupling, and missing edge coverage before style. Consult `references/review-rubric.md` for difficult review judgments; its format is optional.

- Choosing mocks, stubs, fakes, fixtures, or integration tests:
  Prefer the least powerful test double that proves the behavior and adequate contract or integration coverage where adapters can drift. Consult `references/doubles-and-boundaries.md` when the choice is non-obvious; existing coverage counts.

- Tests touch network, waiting, global framework state, environment gates, filesystem/CLI effects, or multiple supported dependency versions:
  Deny unintended effects, reset global state, test relevant configuration dimensions, and assert the exact artifact or capability branch. Consult `references/side-effects-and-compatibility.md` for unresolved isolation or compatibility risks.

## Quick Reference

| Situation | Default action |
|---|---|
| New domain rule | Write one readable example for the normal case and focused examples for meaningful boundaries |
| Test name | State behavior and outcome: `rejects withdrawals that exceed the current balance` |
| Test body | Prefer Arrange / Act / Assert, with setup kept close enough to read as a story |
| Repeated setup | Extract helpers only when the helper name preserves domain meaning |
| Parameterized tests | Use named cases that explain why each row exists |
| Legacy behavior | Add a short rationale: compatibility, data migration, customer contract, bug reference, or explicit unknown |
| Hard-to-test production code | Reuse safe seams; refactor only when necessary, proportionate, and within authorized scope |
| Mock-heavy test | Replace incidental interaction assertions with behavior assertions, fakes, or adapter contract tests |
| Edge case | Name the boundary, not just "handles invalid input" |
| Network or subprocess in tests | Fail on unplanned calls; explicitly fake, stub, or integrate only the contract under test |
| Sleep or retry delay | Replace real waiting with a fake scheduler/clock and assert the requested delay when it is behavior |
| Global framework state | Restore a known baseline before each test and clean up afterward when the framework cannot isolate it |
| Configurable behavior | Cover the dimensions in its contract: usually default/override/effect, plus environment or capability branches only when relevant |
| File or CLI effect | Assert exit/result plus the exact path, type, contents, backup, and unchanged-on-cancel behavior that matter |
| Compatibility promise | Exercise the lowest supported combination and current versions; add capability-present/absent paths when production has an optional capability |
| Review | Ask whether the test would teach a new maintainer what behavior matters |

## Core Rules

1. Treat tests as living documentation. A reader should learn the feature, its vocabulary, and its important boundaries from the test names and examples.
2. Prefer behavior names over implementation names. Test `rejects expired invitations`, not `returns false from validateInvite`.
3. Keep examples concrete and domain-shaped. Use real values, currencies, roles, states, dates, and IDs when they clarify the rule.
4. Make intent local. A test should not require reading a distant fixture factory, hidden global setup, or framework magic before the behavior makes sense.
5. Use DAMP tests when readability and DRY conflict. Duplication that keeps the scenario clear is often better than clever shared setup.
6. Keep each test focused on one behavior, but assert every outcome needed to prove that behavior. State changes, returned results, and emitted events can belong together when they are one observable rule.
7. Choose test doubles by contract: stubs answer queries, fakes model simple state, spies observe important effects, mocks enforce essential interactions only.
8. Do not expose private internals, freeze bad abstractions, or add broad interfaces just to make a test pass. Prefer existing safe seams; reshape a production boundary only when necessary and proportionate, and never exceed a tests-only scope.
9. Document edge cases and legacy behavior where the name alone cannot carry the reason. The future reader needs to know whether behavior is principled, historical, contractual, or temporary.
10. Keep tests deterministic. Control time, randomness, external services, locale, timezone, concurrency, and persistence at clear boundaries.
11. Verify the failure mode, not only the happy path. A regression test should fail for the bug it guards against.
12. Match the local test framework and style before importing a new pattern.
13. Make unintended effects fail fast in the test harness. Unstubbed network calls, real sleeps, destructive commands, and shared process state should never pass unnoticed.
14. Assert the real observable with the right subject and type. A boolean existence check compared with file contents, or a correct assertion against the wrong path, is a false positive.
15. For configurable behavior, test the contract's decision dimensions separately from the effect. Exercise capability-present and capability-absent paths when production supports an optional capability.

## Maintainable Test Gate

Before finishing test changes, run this gate mentally and with local tooling where available:

| Gate | Pass condition |
|---|---|
| Intent | The test name says the behavior and expected outcome in domain language |
| Story | Arrange / Act / Assert or equivalent phases are easy to see |
| Evidence | Assertions prove observable behavior rather than incidental implementation |
| Fixtures | Setup is small, named, and close enough to understand without archaeology |
| Edge cases | Boundary scenarios are explicit and explain why the boundary matters |
| Legacy context | Historical or compatibility behavior has a rationale or ticket reference |
| Determinism | Time, randomness, I/O, network, database, and process state are controlled |
| Isolation | Unplanned network, waits, destructive commands, and leaked global framework state fail or are reset explicitly |
| Compatibility | Lowest/current supported combinations are exercised, plus capability-present/absent branches when an optional capability is part of the promise |
| Artifact evidence | Assertions inspect the exact path, value type, contents, and unchanged state that prove the effect |
| Doubles | Mocks, stubs, fakes, and spies are the least powerful option that proves the rule |
| Production design | Safe existing seams are used; any production refactor is necessary, proportionate, and authorized |
| Handoff | A new maintainer can use the tests as an onboarding map for the behavior |

## Operating Workflow

Keep small edits small: use focused context and adequate existing coverage, without a written story or fixed report template.

1. Recon first.
   Read nearby tests, fixtures, factories, helpers, and the production code path before adding patterns.

2. Identify the behavior story.
   Identify the rule and keep unrelated concerns separate. Write it down only when that helps resolve ambiguity.

3. Pick examples.
   Check existing coverage, then choose missing normal, boundary, or failure cases that explain real product risk.

4. Shape the code for observability.
   Use existing safe seams, including scoped legacy patches with reliable restoration and isolation. If none can prove the behavior safely, propose the smallest production refactor and perform it only within authorized scope. Do not use real side effects or leaked globals to avoid that limit.

5. Write the test as documentation.
   Keep setup meaningful, action obvious, and assertions specific. Add a short comment only for history, invariants, or non-obvious domain tradeoffs.

6. Verify failure and readability.
   Run the focused test. When feasible, make sure it fails before the fix or would fail for the guarded regression. Re-read it as onboarding material.

7. Report plainly.
   Report the behavior covered, verification, and remaining risk; mention boundary decisions only when consequential. Omit empty sections and routine process narration.

## Optional Helper

Use the helper as a fast review prompt scanner, not as a verdict:

```bash
python3 scripts/analyze_maintainable_tests.py /path/to/project
python3 scripts/analyze_maintainable_tests.py /path/to/project --json
```

The helper filters directory scans to conventional test paths plus annotated Rust source, while an explicitly supplied supported source file is inspected directly; recognized declarations are checked for a bounded set of name, assertion, fixture, double, coupling, wall-clock, real-sleep, randomness, and legacy-rationale signals, and network access is not detected. A quiet scan does not prove the suite is good, and a noisy scan does not prove the tests are wrong.

## When Guidance Stops Helping

If a bundled testing pattern fails or conflicts with the repository's runner, check its installed version and official framework documentation. Prefer the idiomatic way to prove the behavior while retaining side-effect isolation; mark unexecuted checks honestly. Propose a canonical skill correction or deletion with the source/version and a distinguishing regression. Do not silently edit installed copies or add brittle tests merely to satisfy this skill's examples.

## Reading Guide

| Need | Read |
|---|---|
| Principles behind the defaults | `references/principles.md` |
| Naming tests as behavior documentation | `references/naming-and-intent.md` |
| Arrange / Act / Assert, fixtures, datasets, and helpers | `references/structure-and-fixtures.md` |
| Mocks, stubs, fakes, boundaries, and production-code decomposition | `references/doubles-and-boundaries.md` |
| Legacy systems, characterization tests, and regression rationale | `references/legacy-and-characterization.md` |
| Side-effect isolation, configuration matrices, exact artifact assertions, and compatibility testing | `references/side-effects-and-compatibility.md` |
| Severity-first review of test diffs | `references/review-rubric.md` |
| Common traps and anti-patterns | `references/gotchas.md` |
| Source influence and adaptation notes | `references/source-notes.md` |

## Gotchas

1. A test can be short and still unreadable if the important story is hidden in factories or generic helpers.
2. A test can be duplicated and still maintainable when the duplication keeps independent behaviors obvious.
3. Mock-heavy tests often document implementation decisions, not product behavior. Use mocks when the interaction is the behavior.
4. Parameterized tests become opaque when each row is just data. Name the cases and keep expected outcomes visible.
5. Legacy tests without rationale freeze confusion. Say whether the behavior is intentional, historical, temporary, or unknown.
6. Do not accept painful tests as inevitable. Pain can be design feedback from production code that needs a clearer boundary.
7. A plausible matcher can still prove nothing when its subject has the wrong type or points at the wrong artifact. Trace every assertion back to the observable contract.
8. Passing only on the newest dependency does not prove the advertised compatibility range. Test the oldest supported combination and optional-capability fallback.
