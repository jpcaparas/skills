# Dependency Boundaries

Use this reference when code is difficult to mock, stub, or run in a deterministic test.

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

## Boundary Targets

Move these to an outer boundary or pass them in when behavior depends on them:

| Dependency | Typical replacement |
|---|---|
| Clock or scheduler | Clock function, time provider, scheduler interface, test timer |
| Random or ID generator | Generator function, seeded generator, deterministic ID provider |
| Environment or config | Config object, settings provider, explicit parameter |
| Network or SDK client | Adapter, gateway, narrow client protocol, fake service |
| Database or repository | Repository interface, transaction boundary, in-memory fake |
| Filesystem | File store interface, temp directory fixture, in-memory store |
| Queue, pub/sub, email, SMS | Port/adapter, fake publisher, outbox table, captured message sink |
| Framework context | Handler adapter that maps framework objects into plain inputs |

## Refactoring Pattern

1. Characterize current behavior if it is non-trivial.
2. Identify the hard dependency and the behavior that actually needs it.
3. Introduce a narrow replacement point at the closest stable boundary.
4. Move construction to the composition root, handler setup, fixture, or factory.
5. Add tests that replace the dependency and cover at least one failure path.
6. Keep one integration or contract check around the real adapter when drift matters.

## Good Boundaries

A good boundary:

- Names the caller's need, not the vendor's product line.
- Keeps production wiring visible.
- Lets tests replace behavior without global mutation.
- Avoids leaking transport details into domain rules.
- Has a small contract that can be faked honestly.

## Bad Boundaries

Watch for:

- A generic `Service` or `Manager` that hides unrelated dependencies.
- A dependency container passed everywhere as a service locator.
- Public setters added only for tests.
- Interfaces that mirror every concrete class method exactly.
- Mocks that need long chains of setup to make one behavior pass.
- Tests that patch module globals because no real replacement point exists.

## Language-Agnostic Examples

Prefer this shape:

```text
handler/framework code
  -> parse request
  -> call policy/service with explicit collaborators
  -> map result to response

policy/service
  -> deterministic decisions
  -> calls narrow collaborator contract when an effect is required

adapter
  -> translates narrow contract to SDK, database, filesystem, or network
```

Over this shape:

```text
policy/service
  -> reads environment
  -> builds SDK client
  -> calls network
  -> gets current time
  -> mutates global cache
  -> decides business result
```

## See Also

- `test-doubles.md` for choosing the replacement once the boundary exists.
- `gotchas.md` for common overcorrections.
