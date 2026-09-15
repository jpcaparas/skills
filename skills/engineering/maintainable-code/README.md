# maintainable-code

Installable passive skill for keeping generated code maintainable, properly decomposed, strongly typed where the codebase supports it, commented where context matters, resilient to production failures, and easy to isolate in tests. It absorbs the former `maintainable-app` and `mockable-code` skills into one package.

## Install

```bash
npx skills add jpcaparas/skills --skill maintainable-code
```

## Highlights

- `SKILL.md` as the canonical workflow
- `references/principles.md` for core maintainability defaults
- `references/decomposition.md` for splitting functions, modules, and responsibilities
- `references/commenting.md` for useful developer comments with language-specific examples
- `references/review-rubric.md` for severity-first review across maintainability, resilience, and testability
- `references/implementation-plans.md` for self-contained handoff plans
- `references/guardrails-and-quality-gates.md` for strict defaults, dangerous-effect safety, compatibility, and executable checks
- `references/resilience.md`, `references/jobs-and-queues.md`, `references/distributed-systems.md`, and `references/observability.md` for self-healing production behavior
- `references/dependency-boundaries.md` and `references/test-doubles.md` for replaceable dependencies and test doubles
- `references/gotchas.md` for common traps
- `scripts/analyze_maintainability.py`, `scripts/analyze_app_resilience.py`, and `scripts/analyze_mockability.py` as lightweight smell scanners

Use this whenever an agent is writing, refactoring, reviewing, or planning durable code and needs to keep future maintenance cost low. The canonical exclusions for non-code writing, one-off shell commands, and intentionally throwaway code remain in `SKILL.md`.
