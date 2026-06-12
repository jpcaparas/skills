# Mockability Gotchas

Use this when a codebase is technically testable but still awkward, brittle, or misleading.

## Common Traps

1. Interface inflation.
   Adding an interface for every class creates noise without improving substitution. Add contracts at dependency ownership boundaries or where a real fake, stub, or adapter exists.

2. Mocking the design instead of the behavior.
   A test that asserts every internal call usually freezes implementation. Assert outcomes unless call shape is the actual contract.

3. Production wiring with no coverage.
   Injected dependencies can make unit tests pass while the real application cannot construct the graph. Keep a smoke, integration, or contract test for wiring that matters.

4. Hidden deterministic dependencies.
   Clocks, random values, environment reads, locale, timezone, current user, and process-wide context can make tests flaky even without network or database calls.

5. Test-only APIs.
   Public setters, mutable globals, or flags added only for tests weaken production design. Prefer explicit construction, parameters, fixtures, or framework-supported overrides.

6. Over-faking external systems.
   An in-memory fake can drift from a database, broker, or external API. Use fakes for behavior speed, then backstop risky translation with contract or integration checks.

7. Monkeypatch dependency.
   Patching module globals is sometimes the least disruptive move in legacy code, but new core code should usually expose a clearer replacement point.

8. Async and scheduler leaks.
   Sleeps, real timers, background jobs, and unjoined tasks make tests slow or flaky. Prefer controllable schedulers, explicit await points, captured queues, or deterministic job runners.

9. Constructor work.
   Constructors that call networks, read files, start threads, or inspect environment are hard to replace and hard to fail safely. Move effects into explicit start/connect/load calls or outer wiring.

10. Vendor-shaped domain code.
    Passing vendor SDK objects deep into business logic couples tests to transport details. Translate at an adapter boundary into domain-shaped data where practical.

## Repair Heuristic

When a test cannot replace a dependency, ask:

1. Is the dependency needed for the behavior under test?
2. Who should own creating it in production?
3. What is the smallest contract the behavior needs?
4. What double would honestly model it?
5. What adapter or integration check prevents drift?

Stop once the current risk is verifiable. Do not keep abstracting after the dependency is replaceable and the production path remains clear.

## See Also

- `principles.md` for defaults.
- `review-rubric.md` for prioritizing findings.
