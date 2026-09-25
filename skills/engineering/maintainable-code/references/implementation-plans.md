# Implementation Plans

Use this when writing a plan for another agent, teammate, or future session.

## Principle

The plan is a maintenance artifact. It must be executable by someone who has not seen the conversation and cannot infer your unstated intent.

Give the executor enough context to preserve the outcome and constraints, while leaving local implementation choices to their judgment.

## Optional Plan Structure

Scale the plan to uncertainty and risk. The following sections are prompts for a complex handoff, not eight mandatory headings. A small change may need only its scope, intended outcome, and verification evidence.

```markdown
# Plan: <specific outcome>

## Context
- Repository facts, framework, package manager, and local conventions.
- Why this change matters.
- What is explicitly out of scope.

## Current State
- Exact files and symbols involved.
- Short excerpts or descriptions of the current behavior.
- Existing tests or gaps.

## Target Shape
- Responsibilities after the change.
- New or changed types, modules, boundaries, and naming.
- Where comments are needed to preserve non-obvious system context.
- How this matches existing patterns.

## Steps
1. Small ordered implementation step.
2. Verification command or expected observation for that step.

## Tests
- Tests to add or update.
- Existing test pattern to copy.
- Edge cases that must be covered.

## Verification
- Exact commands.
- Expected result.
- What to do if a command is unavailable or already failing.

## Stop Conditions
- Facts that mean the executor should stop and report back.
- Files or behavior that must not be changed.

## Review Notes
- Maintainer risks to inspect after implementation.
- Follow-up work not included in this plan.
```

## Plan Quality Gate

A plan should provide enough evidence to act without guessing about consequential decisions:

- State the outcome and scope without relying on "as discussed."
- Identify affected files or symbols precisely enough to locate the work; do not invent paths not yet inspected.
- Define observable completion criteria and relevant checks, with exact commands when known.
- Note material uncertainty, permission limits, and discoveries that require stopping.
- Check existing coverage before prescribing new tests or characterization.
- Justify new abstraction with real variation or a boundary to protect.

## Dependency Ordering

Put risky refactors behind adequate verification. Reuse existing tests; add characterization only where important behavior is unprotected. Order implementation steps by real dependencies rather than requiring every phase below:

1. Establish or repair verification baseline.
2. Fill consequential coverage gaps around current behavior.
3. Rename and isolate obvious concepts.
4. Move behavior behind clearer boundaries.
5. Replace or remove old paths.
6. Clean up dead code after tests pass.

## Writing for Weak Executors

Spell out the obvious if missing it would cause damage:

- "Do not change public API response fields."
- "Keep this file server-only."
- "Use the existing `ApiError` class instead of adding a new error type."
- "If the import cycle appears, stop and report back."
- "Do not update snapshots until behavior is confirmed."
- "Add a short phase comment before the artifact-download pipeline; future maintainers should not have to reverse-engineer the `gh`/`jq` data flow."

Avoid prescribing trivia that the executor can safely infer from the codebase.

## See Also

- `references/principles.md`
- `references/decomposition.md`
- `references/commenting.md`
