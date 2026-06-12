# Mockability Principles

Use these principles when the SKILL.md gate is not enough.

## Prime Directive

Mockable code lets tests replace expensive, flaky, slow, irreversible, or externally owned collaborators while keeping production behavior clear. The point is not to maximize mocks. The point is to make important behavior verifiable with bounded risk.

## Practical Defaults

1. Explicit collaborators beat hidden collaborators.
   Dependencies that affect behavior should be visible in the function, constructor, module, handler, context, or provider that owns them.

2. Deterministic core, effectful shell.
   Keep domain decisions, validation, authorization checks, pricing rules, retries, and mappings separate from network, database, filesystem, queue, time, randomness, and process reads.

3. Narrow contracts beat broad dependency surfaces.
   Accept the operations the caller needs. Do not pass a full SDK client when one method or a small protocol would communicate the real dependency.

4. Default wiring should remain boring.
   Production construction should be easy to follow. Tests should override collaborators through normal extension points, not hidden global toggles.

5. Test doubles should match the risk.
   Use stubs for canned data, fakes for stateful behavior, spies for observations, mocks for important interaction contracts, and contract/integration tests for adapter drift.

6. Local conventions matter.
   A functional codebase may prefer parameters and pure functions. An object-oriented codebase may prefer constructor injection or interfaces. A framework may provide dependency containers or fixtures. Match the local idiom unless it is the source of the problem.

## Human Review Checks

Ask these questions before finishing:

- Can tests simulate success, failure, timeout, empty, and malformed dependency responses?
- Can time and randomness be controlled without sleeping or hoping?
- Can configuration be varied per test without mutating process-wide state?
- Is there one obvious production wiring path?
- Does the contract name describe caller intent rather than vendor mechanics?
- Would an in-memory fake be simpler and more stable than a deep mock chain?
- Is at least one adapter or contract test protecting the boundary from drift?

## Balancing Forward Progress

Do not turn a small change into a dependency injection rewrite. If a dependency is already isolated well enough for the current risk, leave it alone. If the code is untestable because of a hardcoded effect, add the smallest replacement point and a focused regression test.
