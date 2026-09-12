# Dependency Boundaries

Use this reference when code is difficult to mock, stub, or run in a deterministic test.

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
