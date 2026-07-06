# Source Notes

Primary sources this skill's guidance is adapted from, plus adaptation notes. Verify against these when tooling versions move.

## Foundational

- Parse, don't validate — Alexis King: https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/
  Basis for Principle 2 and every "parse at the boundary" rule. The core idea — record shape knowledge in types rather than discarding it — is language-independent.

## PHP

- Type declarations and `strict_types`: https://www.php.net/manual/en/language.types.declarations.php
  Confirms coercion semantics without `strict_types=1` and the per-file, caller-side scope of the declaration.
- Enumerations: https://www.php.net/manual/en/language.enumerations.php
  Backed enums, `from`/`tryFrom` parsing semantics.
- PHPStan rule levels: https://phpstan.org/user-guide/rule-levels
  Level 9 = strict `mixed` handling, level 10 stricter still; informs the "level 9+" baseline.
- PHPStan baseline workflow: https://phpstan.org/user-guide/baseline
  The ratchet mechanism recommended for legacy adoption.
- Larastan: https://github.com/larastan/larastan
  Eloquent-aware static analysis; relation generics syntax.

## TypeScript

- tsconfig `strict` and related flags: https://www.typescriptlang.org/tsconfig/#strict
  Umbrella flag composition; `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes` are separate opt-ins.
- The `unknown` type (release notes): https://www.typescriptlang.org/docs/handbook/release-notes/typescript-3-0.html
  `unknown` vs `any` semantics underpinning the boundary-parsing rules.
- typescript-eslint strict-type-checked preset: https://typescript-eslint.io/users/configs/
  Mechanical enforcement for the `any` ban (`no-explicit-any`, `no-unsafe-*`).
- Zod: https://zod.dev/
  Schema-first parsing and `z.infer` type derivation used in golden references.

## Python

- mypy strict mode and existing-code adoption: https://mypy.readthedocs.io/en/stable/existing_code.html
  Source of the per-module override ratchet pattern.
- Pyright configuration: https://microsoft.github.io/pyright/#/configuration
  `typeCheckingMode: strict` semantics.
- typing module (`Protocol`, `Literal`, `NewType`, `TypeGuard`, `assert_never`): https://docs.python.org/3/library/typing.html
- PEP 695 (generics syntax): https://peps.python.org/pep-0695/
- PEP 692 (`Unpack[TypedDict]` for kwargs): https://peps.python.org/pep-0692/

## C#, Java, Kotlin

- C# nullable reference types: https://learn.microsoft.com/en-us/dotnet/csharp/nullable-references
  Compile-time-only nature and dependency caveats noted in gotchas.
- Java sealed classes (JEP 409): https://openjdk.org/jeps/409
  Sealed interface + record + exhaustive switch pattern.
- JSpecify nullness annotations: https://jspecify.dev/
  Cross-tool null-marking standard recommended for Java.
- Kotlin null safety: https://kotlinlang.org/docs/null-safety.html
  `!!` semantics, elvis operator, platform types at Java interop boundaries.

## Go, Rust, Swift

- Go generics introduction: https://go.dev/blog/intro-generics
  Basis for preferring type parameters over `any` erasure.
- Effective Go (type assertions, switches): https://go.dev/doc/effective_go#interface_conversions
- Rust enums and pattern matching: https://doc.rust-lang.org/book/ch06-00-enums.html
  Exhaustive `match` semantics; newtype guidance from the broader book chapters.
- Clippy `unwrap_used` lint: https://rust-lang.github.io/rust-clippy/master/index.html#unwrap_used
- Swift optionals and enums: https://docs.swift.org/swift-book/documentation/the-swift-programming-language/enumerations/
  Associated values and `@unknown default` handling.

## Gradual and Optional Typing

- TypeScript JSDoc support / `@ts-check`: https://www.typescriptlang.org/docs/handbook/jsdoc-supported-types.html
  The zero-build-step checking path recommended for vanilla JS.
- Sorbet: https://sorbet.org/docs/overview
  `# typed:` sigil levels and `sig` syntax for Ruby projects that opt in.
- Elixir typespecs: https://hexdocs.pm/elixir/typespecs.html
  `@spec`/`@type` conventions consumed by Dialyzer and the gradual type checker.

## Adaptation Notes

- Version-sensitive claims (PHPStan level 10 existence, PEP 695 availability in Python 3.12+, Java 21 pattern matching) are stated with their version gates in the reference files; re-verify when a project pins older toolchains.
- The "one owner per nullable" rule and the fallback-chain refactor are this skill's synthesis; they generalize the null-object pattern and parse-don't-validate rather than quoting a single source.
- Checker strictness recommendations intentionally target the strictest widely adopted level (not the bleeding edge) so the skill stays usable on real teams.
