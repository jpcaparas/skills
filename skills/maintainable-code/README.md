# maintainable-code

Installable passive skill for keeping generated code maintainable, properly decomposed, strongly typed where the codebase supports it, and understandable to human maintainers.

## Install

```bash
npx skills add jpcaparas/skills --skill maintainable-code
```

## Includes

- `SKILL.md` as the canonical workflow
- `references/principles.md` for core maintainability defaults
- `references/decomposition.md` for splitting functions, modules, and responsibilities
- `references/review-rubric.md` for severity-first maintainability review
- `references/implementation-plans.md` for self-contained handoff plans
- `references/gotchas.md` for common traps
- `scripts/analyze_maintainability.py` as a lightweight smell scanner

Use this whenever an agent is writing, refactoring, reviewing, or planning code and needs to keep future maintenance cost low.
