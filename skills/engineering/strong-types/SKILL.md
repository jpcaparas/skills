---
name: strong-types
description: "Passive: apply when writing or reviewing code in a typed language (TypeScript, PHP, Python, C#, Java, Kotlin, Go, Rust, Swift). Replaces any/mixed, untyped signatures, stringly-typed state and blind ??/|| fallback chains with DTOs, enums, unions and strict checker settings. Not for untyped code."
compatibility: "Optional scanner script needs python3."
---

# strong-types

Every value should have one knowable type at every point. If the author cannot say what an expression's type is without running the code, the code is not done. Keep it proportional: for a small edit, check silently and mention only decisions that change the implementation. Use the project's existing checker (tsc, PHPStan, Psalm, mypy, pyright, compiler flags) at its configured level; match or exceed it, run it the supported way, and report pre-existing failures or an unavailable checker rather than weakening settings. Preserve framework or interface type contracts exactly; contain and justify a required escape hatch instead of narrowing a signature incompatibly. Pair with `maintainable-code` when available.

## The core move

```php
$image = $location->preview ?? $location->banner ?? $location->thumbnail;
```

This leaves four questions open: each property's type, which are nullable and why, the type of `$image`, and whether the whole chain can still be `null`. Move the chain into one named, typed owner with an explicit all-null policy, and use that at every call site:

```php
public function primaryImage(): Image
{
    return $this->preview ?? $this->banner ?? $this->thumbnail
        ?? throw new MissingImageException($this->id);
}
```

Fallback chains sometimes hide a schema problem (three image columns nobody normalised); the accessor is a bandage, so note the schema fix.

## Rules

- Fully type every signature: parameters, return (`void`/`None` counts), and thrown types where the language tracks them. Type the boundaries (DTOs, enums, signatures) before the logic.
- `any`, `mixed`, `interface{}`, `Object`, bare `dict`/`array` are escape hatches. Each needs a written reason; default to a concrete type, generic, union, or `unknown`/`object` followed by a parse.
- Parse, don't validate: turn external input (HTTP, JSON, env, DB rows, CLI args) into a named typed structure once at the edge, with a parser that can fail loudly (zod schema, pydantic, typed constructor), and pass only that inward. Data crossing a function boundary gets a named type; raw arrays, dicts and anonymous shapes are for private local plumbing.
- Make illegal states unrepresentable: enums, sealed hierarchies, discriminated unions and `Literal` instead of magic strings or boolean pairs; every switch/match over a closed set is exhaustive by compiler check (`assert_never`, `never`, sealed `when`), not by comment.
- Nullability is a design decision. A field is nullable only when absence is a real domain state, and each nullable read has one owner that resolves it; narrow once at the boundary and keep the non-null type flowing inward. Replace `!!`, force-unwraps, `unwrap()` in production paths with that resolution.
- One variable, one type. Casts move risk rather than remove it: prefer narrowing (guards, pattern matching, `instanceof`); a cast that cannot fail loudly (`as any`, `(array)`, unchecked cast) is not a fix.
- Suppressions (`@ts-ignore`, `# type: ignore`, `@phpstan-ignore`) are fixed, or targeted with the error code and reason.
- Generics preserve types across boundaries; do not erase them (`List<Object>`, `Collection<mixed>`).
- Turn the checker up, not off: strict for new files, baseline or ratchet files for legacy code, burned down gradually. A big-bang retrofit fails, and an ordinary edit is not a tooling rollout.

Per language the baseline is: PHP `declare(strict_types=1)`, typed properties and constructor promotion, enums, DTOs over associative arrays, PHPStan/Psalm (Larastan) generics in docblocks, and for Eloquent, `$casts` plus `@property` annotations so model attributes have types; TypeScript `strict: true`, no `any`/`@ts-ignore`, `unknown` plus parsing, discriminated unions with exhaustive switches; Python full annotations, mypy/pyright strict, dataclasses/TypedDict/pydantic over raw dicts, `Enum`/`Literal` over strings; C# nullable reference types, records, sealed hierarchies; Kotlin no `!!`, sealed types; Go no `interface{}` escape hatches; Rust and Swift newtypes and enums with associated data.

## Where not to push

In plain JavaScript, untooled Ruby, Lua, shell and similar, write defensively and document shapes; do not add a type system, migrate the language or change the project's error-handling regime (no universal `set -euo pipefail` in a quoting fix). Suggest typing tools, such as JSDoc, Sorbet or typespecs, at most once and only when useful.

## Gotchas

- Annotation is not typing: `function f(mixed $x): mixed` is annotated and fully ambiguous. Casting to a green checker is worse than no checker.
- A DTO per boundary is not a DTO per function; reuse domain types across layers that share meaning.
- Type gymnastics are a smell; if a type needs a paragraph of conditional generics, simplify the design.
- When a small fix must keep both of the project's checkers (for example mypy and pyright) passing, run the documented project command, not arbitrary touched files.

## Reviewing

Lead with ambiguity that causes runtime failures: nullable leaks, `any` laundering, unverified casts on parsed JSON, suppressions, stringly-typed status, silent default coercion; then style. Order findings by severity.

## Scanner

`python3 scripts/analyze_type_strictness.py <path> [--json]` surfaces candidate fallback chains, escape-hatch types, untyped signatures, suppressed type errors, missing `strict_types`, and non-strict TypeScript configs. Treat findings as review prompts; a quiet scan does not prove strong typing.
