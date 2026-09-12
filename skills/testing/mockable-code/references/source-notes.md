# Source Notes

This skill distills widely used testing and design practices into agent instructions:

- Hexagonal architecture and ports/adapters for isolating external systems.
- Dependency inversion as a boundary tool, not an interface quota.
- Test double vocabulary from common testing literature: dummy, stub, fake, spy, mock.
- Functional core, imperative shell for deterministic business behavior.
- Contract and integration tests as a backstop for mocked adapters.
- Framework-native override patterns such as fixtures, providers, contexts, and test containers.

The instructions are intentionally language agnostic. Prefer the local codebase's idioms over importing a pattern mechanically.
