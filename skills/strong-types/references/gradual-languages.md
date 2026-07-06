# When Not to Force It

Strong typing is enforced where the language and toolchain can hold it. Where they cannot, forcing type ceremony produces friction without safety. This file defines the boundary and what to do on the untyped side of it.

## The Decision

```
Does the project have a type checker configured and passing?
├── Yes → Enforce this skill at the configured level or stricter.
│
├── No, but the language has mature optional typing
│   (PHP, Python, Ruby+Sorbet/RBS, Elixir, JS→TS migration)
│   ├── You are writing NEW modules → Type the new code fully; propose (not impose)
│   │   adding the checker for it. New code never inherits old looseness.
│   └── You are editing EXISTING untyped code → Match local conventions, add types
│       where they are free (signatures you touch), and suggest a ratchet path once,
│       in the final report, not as a refactor inside the task.
│
└── No, and the language has no practical type system for this context
    (shell, Lua without teal, vanilla JS the team has chosen to keep, Clojure, older codebases)
    → Do NOT force it. Use the defensive substitute practices below.
```

Two failure modes to avoid, both real:

- **Under-enforcement**: writing untyped code in a typed codebase because it was faster. Never acceptable.
- **Over-enforcement**: converting a team's vanilla JS project to TypeScript inside an unrelated bugfix, adding Sorbet to a Rails app that never asked for it, or wrapping a 40-line shell script in typed ceremony. Also never acceptable.

## Vanilla JavaScript (No TypeScript)

Do not add a TS build step uninvited. Free safety that respects the project:

1. **JSDoc types** — checked by editors and optionally by `tsc` with zero build changes:

```javascript
// @ts-check

/**
 * @param {string} userId
 * @param {{ notify?: boolean }} [options]
 * @returns {Promise<Order[]>}
 */
async function loadOrders(userId, options = {}) { ... }

/** @typedef {{ id: string, total: number, status: "pending"|"paid" }} Order */
```

2. `// @ts-check` at file top opts single files into checking — ideal for new files in an old project.
3. Runtime parsing at boundaries (zod works in plain JS) still applies; it needs no type system.
4. Frozen constants for closed sets: `const STATUS = Object.freeze({ PENDING: "pending", PAID: "paid" })`.

Suggesting `checkJs` + JSDoc in the report is appropriate; converting files to `.ts` without being asked is not.

## Ruby

Ruby has two optional systems: Sorbet (`sig` inline annotations, `srb tc`) and RBS (separate `.rbs` files, Steep). Most Ruby codebases use neither.

- If the project already uses Sorbet: match it. New files get `# typed: strict`, signatures use `sig { params(...).returns(...) }`, never downgrade a file's `# typed:` sigil.
- If it does not: write type-revealing Ruby instead —
  - keyword arguments over options hashes (`def charge(amount:, currency:)`),
  - `Struct`/`Data.define` over hash payloads (`Point = Data.define(:x, :y)`),
  - early `raise ArgumentError` guards at public boundaries,
  - YARD `@param`/`@return` docs on public methods.
- Recommending Sorbet/RBS is a one-line suggestion in the report, only when type-related bugs were actually part of the task.

## Elixir

Dynamically typed with gradual tooling: typespecs + Dialyzer, and the gradual set-theoretic type checker landing across recent versions.

- Write `@spec` for public functions and `@type t` for structs — cheap documentation that Dialyzer and the new checker both consume:

```elixir
@type t :: %__MODULE__{id: pos_integer(), email: String.t()}

@spec primary_image(Location.t()) :: {:ok, Image.t()} | {:error, :missing_image}
def primary_image(%Location{} = location) do ...
```

- Pattern matching in function heads is the idiomatic narrowing tool; prefer it over conditional type checks in bodies.
- Structs (`defstruct` + `@enforce_keys`) over bare maps for boundary data.
- Do not bolt Dialyzer onto a project mid-task; suggest it in the report if type confusion caused the bug.

## Shell, Lua, and Friends

No type system worth enforcing. Substitute practices:

- **Shell**: `set -euo pipefail`; quote everything; validate arguments at the top with usage messages; prefer long options for readability; keep scripts short and promote growing ones to a typed language (that promotion is worth suggesting).
- **Lua**: if the project already uses Teal or LuaLS annotations, match them; otherwise use assertion guards at function entry (`assert(type(name) == "string")`) on public boundaries only.
- **Clojure and similar**: the community answer is spec/malli schemas at boundaries, not static types. If the project uses them, match; if not, do not introduce them mid-task.

## Universal Substitute Practices

When you cannot make the checker enforce types, you can still delete ambiguity:

1. Guard clauses at public boundaries that fail fast with named errors — a runtime signature.
2. Named constructors/factories over ad hoc literals, so shapes have one birthplace.
3. Docblocks that state types (`@param`, `@spec`, JSDoc, YARD) — readers and editors benefit even without a checker.
4. Closed sets as frozen constant tables, matched exhaustively with an explicit "unknown value" error branch.
5. Small modules: ambiguity compounds with distance; short files keep untyped shapes traceable.

## How to Suggest (Not Impose) Typing

When a task in an untyped codebase surfaces type-related bugs, end the report with one short, optional note:

> This bug was a shape mismatch that a checker would have caught. If useful, a low-cost path here is `// @ts-check` + JSDoc on new files (no build changes). Happy to set that up as a separate task.

One suggestion, once, scoped, deferred. No unsolicited refactors, no config changes bundled into unrelated work, no lectures.
