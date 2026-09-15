# maintainable-code

Use this skill passively whenever writing, editing, refactoring, reviewing, or planning code. It keeps agent-generated code understandable, decomposed around stable responsibilities, resilient to production failures (retries, duplicates, stuck work), replaceable in tests, and aligned with local repository patterns.

Keep `SKILL.md` authoritative. The wrapper files only describe packaging.

Core references:

- `references/principles.md`
- `references/decomposition.md`
- `references/commenting.md`
- `references/review-rubric.md`
- `references/implementation-plans.md`
- `references/guardrails-and-quality-gates.md`
- `references/resilience.md`
- `references/jobs-and-queues.md`
- `references/distributed-systems.md`
- `references/observability.md`
- `references/dependency-boundaries.md`
- `references/test-doubles.md`
- `references/gotchas.md`

Primary helpers:

- `scripts/analyze_maintainability.py`
- `scripts/analyze_app_resilience.py`
- `scripts/analyze_mockability.py`
