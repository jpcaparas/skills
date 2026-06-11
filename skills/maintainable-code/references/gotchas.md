# Gotchas

Common ways maintainability guidance goes wrong.

## Over-Extraction

Small helpers help only when they name stable concepts. Extracting every branch into a tiny function can create a reading maze.

Repair:

- Keep simple local logic inline.
- Extract named domain concepts.
- Group private helpers near their caller when the language supports it.

## Premature Generality

A generic engine, registry, plugin layer, or rule system is usually more expensive than a few explicit functions until there is real variation.

Repair:

- Keep the first implementation direct.
- Note likely extension points without implementing them.
- Add abstraction when the second or third concrete case proves the axis of change.

## False DRY

Two blocks that look similar may change for different reasons. Merging them creates shared risk.

Repair:

- Ask what business rule owns each block.
- Share pure mechanical transformations.
- Keep policy duplicated until the shared reason to change is real.

## Clean-Code Cargo Culting

Rules like "functions should be tiny" or "comments are bad" are harmful when applied without context.

Repair:

- Prefer local evidence over slogans.
- Explain the maintainer risk.
- Use tests and reviewability as the judge.

## Type Theater

Types that merely rename `string`, `any`, or generic records without constraining behavior can create false confidence.

Repair:

- Use types to encode states, units, variants, and required fields.
- Narrow at boundaries.
- Avoid casting away uncertainty before validation.

## Agent Style Drift

Agents often import habits from other ecosystems: new folder conventions, generic helpers, alternate test frameworks, and unnecessary dependencies.

Repair:

- Read nearby code before editing.
- Reuse existing helpers.
- Add dependencies only when they pay for themselves and fit the project.

## Hidden Error Collapse

Mapping every failure to `false`, `null`, or "Something went wrong" removes the context maintainers need.

Repair:

- Preserve original error context at logs or typed error causes.
- Convert errors at user-facing boundaries.
- Test important failure modes.
