---
name: strong-types
description: "Passive skill enforcing strong typing when writing or reviewing PHP, TypeScript, Python, C#, Kotlin, Go, Rust, or other typed code. Bans any/mixed, untyped signatures, blind ??/|| fallback chains; prefers DTOs, enums, generics, strict flags. Do NOT force typing onto untyped languages."
compatibility: "No external dependencies. Optional helper scripts require python3."
metadata:
  version: "1.0.0"
  short-description: "Enforce strong typing everywhere the language can support it"
  openclaw:
    category: "development"
    requires:
      bins: [python3]
references:
  - principles
  - php
  - typescript
  - python
  - jvm-and-dotnet
  - go-rust-swift
  - gradual-languages
  - review-rubric
  - gotchas
  - source-notes
---

# strong-types

Write, edit, and review code so every value has one knowable type at every point in the program. Type ambiguity is a defect: if the author cannot say what type an expression is without running the code, the code is not done.

## Passive Trigger

Load this skill in the background whenever a coding task touches a language with a real type system — static (C#, Java, Kotlin, Swift, Go, Rust, TypeScript) or gradual with mature tooling (PHP, Python, Ruby with Sorbet, Elixir with typespecs). Apply it to new code, edits, refactors, reviews, and implementation plans alike.

Keep it proportional: for small edits, run a silent type-ambiguity pass and mention only the decisions that change the implementation. Also load {{ skill:maintainable-code }} for general code quality when available. When the language or codebase has no usable type system, read `references/gradual-languages.md` and do not force the issue.

## The Canonical Offense

```php
$image = $location->preview ?? $location->banner ?? $location->thumbnail;
```

This line encodes four unanswered questions: what type is each property, which of them are nullable and why, what type is `$image` afterward, and can the whole chain still be `null`. Strongly typed code answers all four in the signature:

```php
final class Location
{
    public function primaryImage(): Image
    {
        return $this->preview ?? $this->banner ?? $this->thumbnail
            ?? throw new MissingImageException($this->id);
    }
}
```

The fallback logic still exists — but it lives in one named, typed method with an explicit return type, an explicit policy for the all-null case, and a domain name (`primaryImage`) instead of being re-derived inline at every call site. That transformation is the core move of this skill.

## Decision Tree

What are you working on?

- PHP (Laravel, Symfony, plain):
  Read `references/php.md`. Require `declare(strict_types=1)`, typed properties, typed signatures, enums, DTOs over associative arrays, and PHPStan/Psalm-level generics annotations.

- TypeScript or a JS codebase that compiles TS:
  Read `references/typescript.md`. Require `strict: true`, ban `any` and `@ts-ignore`, use `unknown` + parsing at boundaries, discriminated unions, and exhaustive switches.

- Python:
  Read `references/python.md`. Require full signature annotations, mypy/pyright strict mode, dataclasses/TypedDict/pydantic over raw dicts, `Enum`/`Literal` over strings.

- C#, Java, or Kotlin:
  Read `references/jvm-and-dotnet.md`. Require nullable reference types (C#), sealed hierarchies and records, exhaustive pattern matching, and no unchecked casts or `!!`.

- Go, Rust, or Swift:
  Read `references/go-rust-swift.md`. Ban `interface{}`/`any` escape hatches, `unwrap()` in production paths, and force-unwraps; prefer newtypes and enums with associated data.

- Plain JavaScript, Ruby, Elixir, Lua, shell, or another dynamically typed setting:
  Read `references/gradual-languages.md`. Nudge toward available typing tools without rewriting the project or fighting its conventions.

- Reviewing a diff or plan:
  Use `references/review-rubric.md`. Lead with ambiguity that can cause runtime failures: nullable leaks, `any` laundering, stringly typed state, and silent coercion.

- Unsure where to start:
  Read `references/principles.md`, then run the Type Ambiguity Gate below.

## Quick Reference

| Ambiguity smell | Default action |
|---|---|
| `??` / `||` / `or` fallback chain on object properties | Extract one typed method or accessor with an explicit return type and an explicit all-null policy |
| `any`, `mixed`, `interface{}`, `Object`, untyped `dict`/`array` | Replace with a concrete type, generic parameter, union, or `unknown` + parse |
| Untyped function signature | Add parameter and return types before touching the body; `void`/`None` counts |
| Associative array / raw dict / anonymous object crossing a boundary | Define a DTO, dataclass, record, struct, or TypedDict with named typed fields |
| Magic string states (`"pending"`, `"active"`) | Replace with an enum, sealed type, or `Literal` union with exhaustive handling |
| Nullable value passed around "just in case" | Narrow once at the boundary; keep the non-null type flowing inward |
| External input (HTTP, JSON, env, DB row, CLI args) | Parse into a typed structure at the edge; never let raw payload shapes travel |
| Type error suppression (`@ts-ignore`, `# type: ignore`, `@phpstan-ignore`) | Fix the type or document the precise error code and reason inline |
| Casts used to silence the checker (`as any`, `(array)`, `!!`, unchecked cast) | Replace with narrowing, a type guard, or a parse step that can fail loudly |
| Boolean parameter pairs encoding a state machine | Replace with one enum/sealed type so illegal combinations cannot exist |
| Same variable reassigned to different types | Split into separate variables with one type each |
| Weak compiler/checker settings | Turn strictness on for new code; ratchet existing code with baselines |

## Core Rules

1. Every function signature is fully typed: every parameter, the return type, and thrown/raised error types where the language tracks them. An untyped signature is an unfinished signature.
2. `any`, `mixed`, `interface{}`, `Object`, and bare `dict`/`array` types are escape hatches, not types. Each use requires a written justification; the default answer is a concrete type, a generic, or `unknown` followed by a parse.
3. Make illegal states unrepresentable. Prefer enums, sealed hierarchies, discriminated unions, and non-nullable fields over booleans, magic strings, and optional-everything records.
4. Parse, don't validate. Convert untrusted input into a typed structure exactly once at the boundary, and pass only the typed structure inward. Checking a shape without changing the type is wasted work.
5. Data that crosses a function boundary gets a named type. Associative arrays, raw dicts, and anonymous shapes are for private local plumbing only, if at all.
6. Nullability is a design decision, not a default. A field is nullable only when "absent" is a real domain state, and every nullable read has exactly one owner that resolves it. Fallback chains at call sites mean the owner is missing.
7. Keep one variable one type. Reassigning a variable to a different type destroys inference and reader trust.
8. Casts move risk, they do not remove it. Prefer narrowing (type guards, pattern matching, `instanceof`, exhaustive switches) that the checker can verify. A cast that cannot fail loudly is a lie waiting to be believed.
9. Turn the checker up, not off. Strict compiler flags and strict analyzer levels are the baseline for new code; use baseline/ratchet files to adopt them incrementally in legacy code, never blanket suppressions.
10. Generics exist to preserve types across boundaries. A container, repository, or helper that erases types (`List<Object>`, `Collection<mixed>`) forces every caller to cast; parameterize it instead.
11. Exhaustiveness is enforced by the compiler, not by comments. Every switch/match over a closed type handles every case or fails compilation when a case is added.
12. Do not force the issue where the language cannot hold it. In plain JS, untooled Ruby, Lua, or shell, write defensively, document shapes, and suggest — not impose — typing tools. Read `references/gradual-languages.md` first.

## Type Ambiguity Gate

Before finishing a change in a typed language, check:

| Gate | Pass condition |
|---|---|
| Signatures | Every new or edited function has explicit parameter and return types |
| Escape hatches | No new `any`/`mixed`/`interface{}`/bare collection types without an inline justification |
| Boundaries | External input is parsed into named types at the edge; no raw payload shapes travel inward |
| Nullability | Every nullable has one resolving owner; no repeated `??`/`||` fallback chains at call sites |
| States | Closed sets of states use enums/unions with compiler-checked exhaustive handling |
| Casts | No cast that merely silences the checker; narrowing or parsing used instead |
| Suppressions | No new blanket error suppressions; any targeted suppression names the error and the reason |
| Strictness | New files meet the strictest checker level the project supports; ratchet configured for legacy |
| Data shapes | Boundary-crossing data uses DTOs/records/dataclasses, not associative arrays or raw dicts |
| Proportionality | Untyped-language code was not force-converted; guidance stayed advisory |

## Operating Workflow

1. Detect the type regime.
   Identify the language, the checker (tsc, PHPStan, Psalm, mypy, pyright, compiler flags), and the configured strictness before writing code. Match or exceed it; never write below it.

2. Type the boundaries first.
   Define the DTOs, enums, and signatures for data entering and leaving the change before implementing logic. The happy path is easy once the shapes are fixed.

3. Hunt ambiguity in the diff.
   Scan for fallback chains, escape-hatch types, untyped signatures, magic strings, and casts. Each one either gets a concrete type or a one-line justification.

4. Resolve nullability at the source.
   When you find a `?? $b ?? $c` chain, find out why each link is nullable, pick the owner (accessor, factory, database default, parse step), and collapse the chain into one named typed member.

5. Verify with the checker.
   Run the project's type checker at its configured level on the touched files. A green checker at strict level is the acceptance test for this skill.

6. Report plainly.
   Name the types introduced, the escape hatches removed or justified, the nullability decisions made, and any remaining ambiguity with its reason.

## Optional Helper

Use the helper as a fast ambiguity scanner, not as a verdict:

```bash
python3 scripts/analyze_type_strictness.py /path/to/project
python3 scripts/analyze_type_strictness.py /path/to/project --json
```

It flags likely fallback chains, escape-hatch types, untyped signatures, suppressed type errors, missing `strict_types` declarations, and non-strict TypeScript configs. A quiet scan does not prove the code is strongly typed, and a noisy scan does not prove the code is wrong.

## Reading Guide

| Need | Read |
|---|---|
| Universal strong-typing principles and golden references | `references/principles.md` |
| PHP: strict_types, typed properties, enums, DTOs, PHPStan/Psalm generics | `references/php.md` |
| TypeScript: strict flags, any bans, unions, parsing at boundaries | `references/typescript.md` |
| Python: annotations, mypy/pyright strict, dataclasses, Protocols | `references/python.md` |
| C#, Java, Kotlin: nullable refs, records, sealed types, exhaustive matching | `references/jvm-and-dotnet.md` |
| Go, Rust, Swift: escape hatches, newtypes, enums, optionals | `references/go-rust-swift.md` |
| When and how NOT to force typing | `references/gradual-languages.md` |
| Severity-first review of typing diffs | `references/review-rubric.md` |
| Common traps and anti-patterns | `references/gotchas.md` |
| Research sources and adaptation notes | `references/source-notes.md` |

## Gotchas

1. Adding type annotations is not the same as strong typing. `function f(mixed $x): mixed` is annotated and still fully ambiguous.
2. Casting your way to a green checker is worse than no checker: the type system now actively asserts something false.
3. A DTO per boundary does not mean a DTO per function. Over-fragmenting types creates mapping busywork; reuse domain types across layers that genuinely share meaning.
4. Strictness retrofits fail when done as one big bang. Ratchet: strict for new files, baseline for old, burn the baseline down gradually.
5. Fallback chains sometimes hide a data problem, not a code problem. If three image columns exist because nobody normalized the schema, the typed accessor is a bandage — note the schema fix.
6. `unknown` (TS) and `object` are safe defaults for untrusted data; `any` and `mixed` are not. The former force a parse; the latter silently infect everything downstream.
7. Type gymnastics are their own smell. If a type needs a paragraph of conditional generics to express, simplify the design instead of showcasing the type system.
