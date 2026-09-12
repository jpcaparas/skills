# Mockability Review Rubric

Use this rubric when the user asks for a review or when a code change risks making behavior hard to isolate.

## Findings First

Lead with defects and risks, ordered by severity. Cite concrete files and lines when available. Keep style preferences out unless they materially affect testability or future changes.

## Severity Guide

| Severity | Finding type | Why it matters |
|---|---|---|
| Critical | Tests must hit real payment, email, production database, destructive filesystem, or shared service for ordinary behavior | Failures can cost money, mutate real state, or block safe verification |
| High | Business policy is tangled with hardcoded network, database, clock, random, env, queue, or framework state | Important behavior cannot be tested deterministically or safely |
| High | Error, timeout, retry, or partial-failure behavior cannot be simulated | The riskiest paths remain unverified |
| Medium | A broad SDK/client/service is passed where a narrow contract would clarify ownership | Tests become coupled to vendor details and setup grows brittle |
| Medium | Tests overuse mocks for implementation details instead of observable behavior | Refactors break tests even when behavior is preserved |
| Medium | Production wiring is hidden behind globals, service locators, or implicit containers | Replacements are hard to reason about and integration failures hide |
| Low | Names like `MockService` or `Helper` obscure the role of a test double | Readability suffers but behavior may still be safe |

## Review Template

Use this shape:

```markdown
## Findings

- Severity: file:line - Concrete mockability issue.
  Impact: What behavior cannot be isolated or what failure path cannot be simulated.
  Repair: Smallest practical boundary or test-double change.

## Open Questions

- Any dependency ownership or framework lifecycle uncertainty.

## Verification Notes

- Tests or checks run.
- Remaining real-service or contract-test gap.
```

## What Not To Do

- Do not ask for dependency injection everywhere by default.
- Do not require interfaces for value objects, pure functions, or stable internal helpers.
- Do not convert every behavior test into interaction mocks.
- Do not ignore adapter or integration coverage once mocks are introduced.
- Do not recommend monkeypatching as the only long-term strategy for core code.

## See Also

- `boundaries.md` for repair patterns.
- `test-doubles.md` for choosing the right double.
