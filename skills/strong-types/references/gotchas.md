# Gotchas and Anti-Patterns

Tribal knowledge for enforcing strong typing without creating new problems. Organized by category; append new lessons under the matching heading.

## Annotation Theater

- `function f(mixed $x): mixed` and `def f(x: Any) -> Any` are fully annotated and fully ambiguous. Annotation coverage metrics measure typing effort, not typing strength — grep for escape hatches, not for colons.
- A hand-written `.d.ts` or `@property` docblock for a remote system is a *claim*, not a check. Treat self-declared types for external data as untrusted until a parse step enforces them.
- Generated types (OpenAPI, GraphQL codegen, `sqlc`, Prisma) beat hand-written ones for any schema that already exists somewhere else. Duplicated hand-written types drift silently.

## Cast Laundering

- The checker being green means nothing if the diff added casts to make it green. `as any as T`, `(array)`, `!!`, `cast()`, unchecked generics — each converts a compile-time error into a runtime error. In review, a new cast next to a new checker pass is the first thing to inspect.
- Watch for casts hidden in helpers: a `fromArray(array $data): self` that assigns without checking is a cast with a method name. The parse boundary must actually verify.
- Test code gets a modest cast allowance (fixtures are controlled data), but factories with real types are still better — typed fixtures catch schema drift in tests before production does.

## Nullability

- Adding `?`/`| None`/`Optional` to silence a checker error moves the problem to every caller. Ask first: *should* this ever be absent? Usually the producer can guarantee presence (constructor requirement, DB default, parse step) and the nullable disappears.
- Truthiness fallbacks (`or` in Python, `||` in JS) are not null checks: they also swallow `0`, `""`, `false`, and empty collections. When auditing a fallback chain, check whether falsy-but-valid values are being silently discarded — that is a live bug, not just a smell.
- A fallback chain may be a schema problem wearing code clothes. Three nullable image columns often mean the data model needs a single `images` relation with a priority — note the schema fix alongside the typed accessor.

## Enforcement Strategy

- Big-bang strictness retrofits die in review. The working pattern is always: strict for new files, generated baseline for old files, CI fails on baseline growth, baseline shrinks opportunistically.
- Turning on a strict flag without `warnings-as-errors` (or CI enforcement) means the warnings become wallpaper within a month. Strictness that does not fail the build is decoration.
- When two checkers disagree (mypy vs pyright, PHPStan vs Psalm), pick one as CI truth. Chasing green on both burns time on incompatible inference edge cases.
- Do not enable every pedantic flag on day one in a team codebase. `strict` + no-escape-hatch rules deliver most of the value; exotic lints (`exactOptionalPropertyTypes` on a legacy API client) can wait until the team trusts the tooling.

## Over-Typing

- DTO-per-function is mapping busywork. A type earns its existence by having a domain meaning or a distinct boundary. Three `UserSummary`-ish shapes that differ by one field usually mean one type with a clear owner was never designed.
- Branded/newtype everything is noise. Brand values that get *confused* (IDs, money, units) or *validated* (email, slug). `type FirstName = Branded<string>` protects nothing anyone was going to confuse.
- If a type needs recursive conditional generics to express, the design is too clever. Types describe the design; when they stop being readable, simplify the design, not the reader.
- Exhaustive matching on *open* sets (third-party enums that grow, HTTP status codes) needs a designed unknown-case branch (`@unknown default`, catch-all returning an error). Pretending an open set is closed trades one bug class for another.

## Language-Specific Traps

- **PHP**: `declare(strict_types=1)` affects calls *from* the file it appears in — a strictly typed library called from a non-strict file still coerces. Coverage must be every file, not just library files.
- **PHP**: `empty()` and loose `==` bypass all typing discipline (`empty("0")` is true). In typed code, compare explicitly against the state you mean.
- **TypeScript**: types are erased at runtime; `as` survives compilation as nothing. Any guarantee about runtime data must come from a runtime parse, not from the type layer.
- **TypeScript**: `JSON.parse` returns `any`, not `unknown` — it launders silently. Wrap it once (`parseJson(text): unknown`) and ban direct calls in application code.
- **Python**: dataclasses do not validate. `UserId(user_id="oops")` constructs fine; annotations are checked by mypy, not at runtime. Use pydantic/msgspec when construction happens from untrusted data.
- **Python**: `isinstance` cannot check parameterized generics (`isinstance(x, list[str])` is a TypeError). Narrow the container, then the elements, or use a validation library.
- **Go**: `nil` maps read fine but panic on write; a typed `map[string]X` field still needs construction discipline. Zero values are part of Go's type contract — design structs so the zero value is valid or unconstructable.
- **Kotlin/Java interop**: platform types (`String!`) silently disable null checking. Annotate Java sources (JSpecify) or convert at the boundary; do not let platform types propagate.
- **C#**: nullable reference types are compile-time only and off in dependencies compiled without the context. Public API edges still need `ArgumentNullException.ThrowIfNull`.
- **Rust**: `as` numeric casts truncate silently (`u64 as u8`); use `TryFrom` when the range is not statically guaranteed.

## Process

- Fixing type ambiguity in code you were not asked to touch is scope creep. Fix the ambiguity in your diff; list pre-existing ambiguity in the report as follow-up material.
- When a user pushes back on typing ceremony ("just use an array here"), the ceremony might genuinely be disproportionate — a private 5-line helper does not need a DTO. Concede local plumbing; hold the line on boundaries.
- Checker runtime matters. If strict analysis takes minutes, developers stop running it locally and CI becomes the first feedback. Invest in incremental modes (`tsc --incremental`, PHPStan result cache, mypy daemon) as part of the strictness rollout.
