# Decomposition

Use this when splitting functions, files, modules, components, services, or responsibilities.

## Decomposition Test

Split code when the new boundary has a stable reason to exist:

- It isolates I/O from pure policy.
- It names a domain concept.
- It makes invalid states easier to reject.
- It lets tests cover behavior without expensive setup.
- It prevents unrelated reasons to change from sharing the same function or module.
- It matches an existing boundary in the repo.

Do not split code only because it crossed a line-count threshold. A long straight-line function can be clearer than a trail of anonymous helpers.

## Responsibility Layers

Use these layers as a diagnostic, not a mandatory architecture:

| Layer | Belongs here | Should avoid |
|---|---|---|
| Entry point | Routing, argument parsing, request/response shape | Domain decisions buried inline |
| Orchestration | Sequencing collaborators, transactions, retries | Business rules written as glue |
| Domain policy | Pricing, permissions, validation, state transitions | Database calls and UI formatting |
| Transformation | Mapping one typed shape to another | Hidden I/O or global state |
| Infrastructure | HTTP, database, filesystem, queue, cache | Domain policy |
| Presentation | UI state, formatting for humans | Persistence and core domain rules |

It is acceptable for small codebases to combine layers. Combine them deliberately and keep names honest.

## Extraction Heuristics

Prefer extracting when:

- A block needs a domain name to be understood.
- Multiple branches perform the same conceptual step.
- A test would otherwise require unrelated setup.
- The block has its own error handling or invariant.
- A collaborator can be mocked or faked at a natural boundary.

Delay extracting when:

- There is only one caller and the helper name would be vaguer than the code.
- The extracted function would depend on most of the original function's local variables.
- The helper would hide ordering or side effects.
- The abstraction exists only to satisfy a generic pattern.

## Refactoring Sequence

1. Characterize existing behavior with tests or recorded examples.
2. Rename misleading variables and functions before moving code.
3. Extract pure transformations first.
4. Separate policy from I/O next.
5. Move files or introduce modules only after boundaries are visible in code.
6. Run verification after each meaningful step when the code is risky.

## Naming Boundaries

Names should answer what concept changed, not where the code came from.

Poor names:

- `handleData`
- `processStep`
- `utils`
- `common`
- `manager`
- `doBillingThing`

Better names:

- `calculateInvoiceTotal`
- `parseWebhookEvent`
- `buildRetryPolicy`
- `formatCheckoutSummary`
- `assertUserCanManageProject`

## Anti-Fragmentation Rule

If understanding the flow requires jumping through more files than before, the decomposition probably failed. Re-inline, rename, or group helpers near the caller until the story is visible again.

## See Also

- `references/principles.md`
- `references/guardrails-and-quality-gates.md`
- `references/gotchas.md`
