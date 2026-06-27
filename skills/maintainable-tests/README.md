# maintainable-tests

Installable passive skill for writing and reviewing tests that are readable, behavior-focused, useful as onboarding material, and explicit about edge cases, regressions, and legacy rationale.

## Install

```bash
npx skills add jpcaparas/skills --skill maintainable-tests
```

## Includes

- `SKILL.md` as the canonical workflow
- `references/principles.md` for core maintainable-test defaults
- `references/naming-and-intent.md` for behavior-shaped names
- `references/structure-and-fixtures.md` for Arrange / Act / Assert, fixtures, helpers, and assertions
- `references/doubles-and-boundaries.md` for mocks, stubs, fakes, and testability refactors
- `references/legacy-and-characterization.md` for regression and characterization tests
- `references/review-rubric.md` for severity-first test review
- `references/gotchas.md` for common traps
- `scripts/analyze_maintainable_tests.py` as a lightweight review prompt scanner

Use this whenever an agent is writing, refactoring, reviewing, or planning tests that humans must maintain.
