# Gotchas

Use this reference when the map is noisy, missing obvious paths, or likely to be framework-driven.

## Directory Shape Can Mislead

Directory names often describe packaging, not runtime flow. A file under `services/` may be a thin adapter, while the real orchestration lives in a route, hook, job, or workflow file. Verify roles from calls and registrations.

## Textual Search Is Not A Call Graph

The same identifier can appear in comments, tests, docs, types, generated files, fixtures, logs, and unrelated domains. Treat raw matches as leads until you connect them with imports, calls, or registration.

## Imports Are Not Always Execution

Barrel exports, type-only imports, side-effect imports, and generated clients can make a file look important without being part of the runtime path. Distinguish exposure from invocation.

## Dynamic Registration Hides Edges

Frameworks often wire behavior through decorators, naming conventions, dependency injection, file-system routing, plugin registries, service providers, config files, or generated manifests. When imports do not explain the path, inspect registration surfaces.

## Generated Code Can Be Both Central And Disposable

Generated types, clients, route maps, and ORM files may be central evidence for boundaries, but they are rarely good edit targets. Find the source schema, template, spec, or generator input before recommending changes.

## Monorepos Need Boundary Detection Early

In a monorepo, the most important question may be which package owns the behavior. Check workspace manifests, package names, public exports, and dependency declarations before reading every matching file.

## Tests Can Invert The Map

Tests may call internals directly, bypassing real entrypoints. Use tests to understand behavior and likely owners, but do not treat a test path as a production caller unless it mirrors runtime wiring.

## Similar Names Cross Domains

Names like `Session`, `Account`, `Client`, `Order`, and `Event` often appear in multiple bounded contexts. Include parent directories, package names, and adjacent types in evidence to prevent accidental cross-domain maps.

## See Also

- `references/discovery.md` for narrowing broad or ambiguous targets.
- `references/caller-mapping.md` for evidence ranking.
- `references/output-contract.md` for labeling uncertainty clearly.
