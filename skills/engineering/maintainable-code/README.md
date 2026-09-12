# maintainable-code

Installable passive skill for keeping generated code maintainable, properly decomposed, strongly typed where the codebase supports it, commented where context matters, and understandable to human maintainers.

## Install

```bash
npx skills add jpcaparas/skills --skill maintainable-code
```

## Highlights

- `SKILL.md` as the canonical workflow
- `references/principles.md` for core maintainability defaults
- `references/decomposition.md` for splitting functions, modules, and responsibilities
- `references/commenting.md` for useful developer comments with language-specific examples
- `references/review-rubric.md` for severity-first maintainability review
- `references/implementation-plans.md` for self-contained handoff plans
- `references/guardrails-and-quality-gates.md` for strict defaults, dangerous-effect safety, compatibility, and executable checks
- `references/gotchas.md` for common traps
- `scripts/analyze_maintainability.py` as a lightweight smell scanner

Use this whenever an agent is writing, refactoring, reviewing, or planning durable code and needs to keep future maintenance cost low. The canonical exclusions for non-code writing, one-off shell commands, and intentionally throwaway code remain in `SKILL.md`.
