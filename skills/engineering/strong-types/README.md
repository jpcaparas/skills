# strong-types

Installable passive skill that eliminates type ambiguity: no more `$location->preview ?? $location->banner ?? $location->thumbnail` guessing games. Enforces strong typing in any language that can hold it, and deliberately backs off where the language cannot.

## Install

```bash
npx skills add jpcaparas/skills --skill strong-types
```

## Includes

- `SKILL.md` as the canonical workflow: passive trigger, decision tree, core rules, and the Type Ambiguity Gate
- `references/principles.md` for universal strong-typing principles with golden references
- `references/php.md` for strict_types, typed properties, enums, DTOs, and PHPStan/Larastan generics
- `references/typescript.md` for strict flags, the `any` ban, discriminated unions, and boundary parsing
- `references/python.md` for mypy/pyright strict, dataclasses, Protocols, and `assert_never`
- `references/jvm-and-dotnet.md` for C# nullable refs, Java sealed types, and Kotlin null safety
- `references/go-rust-swift.md` for `interface{}` bans, newtypes, and optional discipline
- `references/gradual-languages.md` for when and how NOT to force typing
- `references/review-rubric.md` for severity-first typing reviews
- `references/gotchas.md` for traps like annotation theater and cast laundering
- `scripts/analyze_type_strictness.py` as a lightweight ambiguity scanner

Use this when an agent is writing, editing, reviewing, or planning code and every expression should have one knowable type.
