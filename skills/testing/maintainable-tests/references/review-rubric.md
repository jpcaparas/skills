# Maintainable Test Review Rubric

## Table of Contents

- [Severity Model](#severity-model)
- [Critical Findings](#critical-findings)
- [High Findings](#high-findings)
- [Medium Findings](#medium-findings)
- [Low Findings](#low-findings)
- [Review Checklist](#review-checklist)

---

## Severity Model

Review tests for their ability to prevent regressions and teach behavior. Lead with defects and maintenance risks, not style preferences.

## Critical Findings

Critical issues mean the tests are actively misleading:

- Test passes even when the protected behavior is broken.
- Assertions check only truthiness, existence, snapshots, or call counts while missing the observable rule.
- Test depends on execution order, real time, random data, network, shared infrastructure, or mutable global state in a way that can produce false results.
- Regression test does not reproduce the original bug condition.
- Assertion reads the wrong path, key, artifact, or collaborator and therefore passes while the real effect is broken.
- Matcher compares incompatible subject and expected types in a way that makes a positive or negated result trivial.

## High Findings

High issues create brittle or expensive maintenance:

- Test is tightly coupled to private implementation while the public behavior could be asserted.
- Broad mocks freeze incidental call order or internal decomposition.
- Fixture setup hides the domain state that determines the outcome.
- Production code was changed only to expose internals to tests.
- Legacy or compatibility behavior is pinned without rationale.
- Edge cases likely to fail are missing from a risky behavior change.
- Unplanned network, sleep, subprocess, filesystem, or destructive effects are allowed by the test harness.
- Global framework state leaks between examples or cleanup targets a different artifact than setup created.
- The suite claims a compatibility range but never exercises the lowest supported combination, or omits a capability-absent path when production feature-detects or conditionally compiles an optional capability.

## Medium Findings

Medium issues slow future readers:

- Test names are vague or implementation-shaped.
- Parameterized cases are unnamed or obscure.
- Helpers remove duplication but hide the scenario.
- Too many assertions from unrelated behaviors are grouped together.
- Test data uses meaningless values where realistic values would clarify the rule.
- Comments restate code but omit the reason for the scenario.

## Low Findings

Low issues are polish:

- Local style inconsistencies.
- Phase comments that are redundant but harmless.
- Minor duplication that can remain because it aids readability.
- A helper name could be more domain-specific.

## Review Checklist

Ask:

1. Would this test fail for the bug or behavior it claims to cover?
2. Can a new maintainer understand the rule from the test name and data?
3. Are setup, action, and assertions visually separable?
4. Are mocks proving contracts instead of implementation trivia?
5. Are edge cases named and meaningful?
6. Is historical or legacy behavior explained?
7. Did production code become easier to observe without becoming test-contorted?
8. Were focused tests, typechecks, linters, or local validators run?
9. Does each assertion inspect the exact observable with the expected value type?
10. Do side-effect and compatibility tests cover isolation, cleanup, and the supported decision matrix?

## See Also

- `references/gotchas.md`
- `references/doubles-and-boundaries.md`
- `references/side-effects-and-compatibility.md`
