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

## Comment Starvation

Agent-generated code often starts with clear high-level steps, then drops into dense command pipelines, workflow YAML, migrations, or generated glue with no explanation. It also tends to document only the class or file header while leaving method contracts, property units, and block-level invariants unexplained. This forces future maintainers to reverse-engineer the system from syntax.

Repair:

- Add phase comments before multi-step operational blocks.
- Add method, property, branch, and block comments where that smaller scope carries the real maintenance risk.
- Explain external API contracts, artifact names, cache keys, and failure-mode decisions.
- Write for a junior maintainer with good fundamentals but limited system context.

## Source-Less Claims

Framework and language comments become risky when they make claims without a source. A future maintainer cannot tell whether the note came from official documentation, a stale blog post, local convention, or an agent guess.

Repair:

- Link official docs when they exist and the claim affects correctness, maintainability, security, or upgrades.
- Verify the URL resolves before including it in reusable instructions or review notes.
- Paraphrase the official behavior and keep long explanations in the source, not in the code comment.
- If the claim comes from local evidence instead of docs, point to the file, test, or observed behavior.

## Diagram Drift

ASCII diagrams help when they make state, data flow, or ownership visible. They become harmful when the code changes and the diagram still describes the old branch, queue, retry path, or data shape.

Repair:

- Add diagrams only for concepts that are hard to scan from prose and names alone.
- Keep diagram labels aligned with real functions, states, events, or domain terms.
- Review diagram arrows and surrounding prose together during edits.
- Update stale text and stale diagrams in the same change; do not let them contradict each other.

## Comment Noise

Comments that repeat syntax make useful comments easier to ignore.

Repair:

- Rename or restructure first when code can explain itself.
- Keep comments for why, invariants, tradeoffs, and surprising constraints.
- Remove stale comments when the code no longer matches them.

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

## See Also

- `references/principles.md`
- `references/decomposition.md`
- `references/guardrails-and-quality-gates.md`
