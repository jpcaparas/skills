# Caller Mapping

Use this reference when deciding what counts as upstream, downstream, a boundary, or a verified path.

## Relationship Types

| Type | Meaning | Strong evidence |
| --- | --- | --- |
| Defines | File owns the symbol, route, handler, type, or behavior | declaration, export, route definition, test subject |
| Calls | Code invokes the target directly | function call, method call, constructor use, component render |
| Registers | Framework/container wires the target into runtime | route table, decorator, DI binding, plugin registration, job config |
| Imports | File depends on a module, but may not execute it directly | import/require/use statement |
| Observes | Test, metric, log, or fixture references behavior | focused tests, dashboards, log keys, metric names |
| Delegates | Target hands work to another module | service call, repository call, adapter call, publish/enqueue |
| Persists | Target reads/writes durable state | SQL, ORM model, migration, cache, object store |
| Crosses | Target crosses a boundary | process, network, package, service, queue, DB, feature flag |

Do not collapse these into one generic "uses" relationship. The distinction is the map.

## Verification Ladder

Rank evidence from strongest to weakest:

1. Runtime wiring: route tables, command registration, queue subscription, framework decorators, DI container bindings.
2. Direct invocation: function/method calls with imports resolved to the target.
3. Focused tests: tests that instantiate or call the target in the same path.
4. Public exports: index files or package entrypoints that expose the target.
5. Textual matches: same name in code, comments, docs, or strings.

Present a relationship as verified only when it reaches levels 1-3. Label levels 4-5 as exposure or leads.

## Tracing Strategy

Trace outward in rings:

```text
entrypoint or public export
  -> caller/orchestrator
  -> target
  -> downstream service/repository/adapter
  -> external boundary or state
```

For each ring, keep only relationships that explain how execution or data moves. Shared constants, type-only imports, generated barrels, and broad utility modules usually belong in evidence notes rather than the core map.

## Language And Framework Hints

| Ecosystem | Common hidden caller source |
| --- | --- |
| React/Next.js | file-system routes, server actions, hooks, event handlers, layout nesting |
| Express/Fastify/Nest | router registration, middleware order, decorators, module providers |
| Rails | routes.rb, controllers, callbacks, ActiveJob, concerns |
| Django/FastAPI | urls.py, routers, dependency injection, management commands |
| Laravel | routes files, service providers, queued jobs, model observers |
| Spring | annotations, component scanning, configuration classes, scheduled jobs |
| Go services | interface implementations, init registration, HTTP mux setup |
| Rust | trait implementations, feature-gated modules, route/service builders |

When the framework is convention-heavy, inspect config and registration files before assuming imports reveal execution.

## Boundary Labels

Call out boundaries explicitly:

- Package boundary: public API, workspace package, library/application split.
- Runtime boundary: frontend/backend, worker/web, CLI/server, browser/server.
- Persistence boundary: database, cache, object store, local file, search index.
- Network boundary: HTTP client, RPC, SDK, webhook, event stream.
- Ownership boundary: team area, domain module, plugin extension point.
- Generated boundary: generated types, compiled artifacts, codegen inputs.

## See Also

- `references/discovery.md` for finding candidate entrypoints and center files.
- `references/output-contract.md` for wording verified vs inferred caller paths.
- `references/gotchas.md` for failure modes around dynamic dispatch and generated code.
