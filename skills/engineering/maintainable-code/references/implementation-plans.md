# Implementation Plans

Use this when writing a plan for another agent, teammate, or future session.

## Principle

The plan is a maintenance artifact. It must be executable by someone who has not seen the conversation and cannot infer your unstated intent.

This adapts the strongest idea from shadcn/improve: a capable agent should spend its judgment on understanding, prioritizing, and specifying; the executor should receive a self-contained plan with enough context to avoid improvising.

## Required Plan Sections

Use this structure unless the user requested another format:

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

A plan is not ready if:

- It refers to "as discussed" or "the above pattern."
- It omits exact file paths.
- It tells the executor to "clean up" without a boundary.
- It lacks verification commands.
- It lacks stop conditions for ambiguous discoveries.
- It assumes tests exist without checking.
- It asks for broad abstraction before proving real variation.

## Dependency Ordering

Put risky refactors behind safety work:

1. Establish or repair verification baseline.
2. Add characterization tests around current behavior.
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
