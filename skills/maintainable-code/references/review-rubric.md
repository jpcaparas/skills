# Review Rubric

Use this for code review, self-review, or final diff inspection.

## Output Order

Lead with findings, ordered by maintainer impact:

1. Behavior or data correctness risk
2. Test gaps that make future change unsafe
3. Confusing ownership or boundaries
4. Over-generalized or under-named abstractions
5. Error handling and observability gaps
6. Missing developer context in dense operational, generated, or cross-boundary code
7. Local consistency, style, and nits

Do not lead with compliments or broad summaries. If there are no findings, say that clearly and mention residual risk.

## Finding Format

Each finding should include:

- Severity: P0, P1, P2, or P3
- File and line
- Concrete maintainer impact
- Why the current shape is risky
- A repair direction, not necessarily a full patch
- Whether tests should change

Example shape:

```text
[P2] Keep retry state out of the shared client singleton
src/api/client.ts:84
The retry counter is stored on the client instance, so concurrent requests can affect each other's retry budget. Keep retry state inside the request call and add a concurrency-focused regression test.
```

## Maintainability Smells

Treat these as leads to inspect, not automatic failures:

- A function mixes validation, I/O, policy, and presentation.
- A generic class replaces a small set of clear functions.
- New configuration accepts arbitrary strings or untyped dictionaries.
- A helper name describes mechanics instead of domain meaning.
- Tests assert implementation calls but not behavior.
- The change creates a second pattern beside an existing local pattern.
- A catch block drops context or converts all failures into the same error.
- A CI workflow, shell script, migration, generated file, or config block has dense command logic without comments explaining phases, invariants, or external contracts.
- A module named `utils`, `common`, or `helpers` becomes a dumping ground.

## Review Discipline

Technical facts beat preferences. If a design choice is merely different from your taste but consistent, tested, and understandable, do not block on it.

Use "nit" only for non-blocking polish. Do not disguise design concerns as nits.

When recommending extraction, name the boundary and why it will change independently. If you cannot do that, recommend renaming or local simplification instead.

## Self-Review Checklist

Before handing off a diff:

- Re-read the changed files without relying on session memory.
- Check that each new name carries domain meaning.
- Check that failure paths preserve useful context.
- Check that tests would fail before the fix or protect the new contract.
- Check that generated code did not introduce a parallel style.
- Check that comments teach non-obvious context instead of narrating syntax.
- Check that any TODO has an owner, reason, or follow-up path.
