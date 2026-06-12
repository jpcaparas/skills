# mockable-code

Installable passive skill for keeping generated and edited code mockable, stubbable, and test-double-friendly without adding needless abstraction.

## Install

```bash
npx skills add jpcaparas/skills --skill mockable-code
```

## Includes

- `SKILL.md` as the canonical workflow
- `references/principles.md` for mockability defaults
- `references/boundaries.md` for isolating dependencies and side effects
- `references/test-doubles.md` for choosing mocks, stubs, fakes, spies, and contract tests
- `references/review-rubric.md` for severity-first mockability review
- `references/gotchas.md` for common traps
- `scripts/analyze_mockability.py` as a lightweight review prompt scanner

Use this whenever an agent is writing, refactoring, reviewing, or planning code that should be easy to test without real external dependencies.
