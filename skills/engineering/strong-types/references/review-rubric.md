# Type-Strictness Review Rubric

Severity-first rubric for reviewing diffs and plans against this skill. Lead with what breaks at runtime; end with style.

## Review Order

Review in this order and report in this order. Stop escalating style points when higher-severity findings exist.

### Severity 1 — Ambiguity that will fail at runtime

- Untrusted input (HTTP, JSON, env, queue, DB JSON columns) used without parsing into a typed structure.
- Casts or assertions that can be wrong: `as User` on parsed JSON, single-value Go type assertions, `!!`, force-unwraps, `Optional.get()` without proof, null-forgiving `!` without adjacent evidence.
- Nullable values dereferenced on some paths: missed narrowing, truthiness checks (`or` /`||`) that swallow `0`/`""`/`false`.
- Closed-set switches with silent `default` fallthroughs that will absorb future states.
- Error-suppression comments (`@ts-ignore`, bare `# type: ignore`, blanket `@phpstan-ignore`) hiding real type errors.

### Severity 2 — Ambiguity that will fail on change

- New `any`/`mixed`/`interface{}`/`Object`/bare `dict`/`array` types without justification — correct today, unverifiable tomorrow.
- Fallback chains (`?? … ?? …`, `|| … || …`, `a?.b ?? c?.d`) at call sites instead of one typed owner.
- Boundary-crossing data as associative arrays / raw dicts / anonymous shapes instead of named types.
- Magic strings for states; boolean parameter pairs encoding state machines.
- Unparameterized generics (`List<Object>`, `Collection` raw, unannotated `array` returns) forcing caller casts.
- Duplicated parallel type definitions that will drift (hand-written type next to a schema that already defines it).

### Severity 3 — Ambiguity that costs readers

- Missing return type annotations; missing `-> None`/`void`.
- Variables reassigned across types; single-letter shape-shifting accumulators.
- Nullable fields whose "why can this be absent?" has no answer in the name, type, or comment.
- Primitive obsession on confusable values (two `string` IDs in one signature).
- Checker strictness lowered, or a baseline grown, without a stated reason.

### Severity 4 — Style within the type system

- `unknown`/`object` where a precise type is one import away.
- Over-broad unions where the actual value set is smaller.
- Type gymnastics: conditional-generic constructions that a simpler design would avoid.
- DTO fragmentation: three near-identical shapes where one domain type would do.

## Reviewer Checklist

Run these questions against every diff in a typed language:

| # | Question | If no |
|---|---|---|
| 1 | Can I state the type of every changed expression without running the code? | Locate the ambiguity source; it is one of the findings above |
| 2 | Do all new/edited signatures have full parameter and return types? | S3 finding, S2 if the function is a boundary |
| 3 | Does external data get parsed exactly once at the edge? | S1 finding |
| 4 | Does every nullable have one resolving owner? | S2 finding; look for the fallback chain |
| 5 | Are new escape-hatch types justified inline? | S2 finding |
| 6 | Do closed-set branches fail compilation when a case is added? | S2 finding |
| 7 | Are all casts adjacent to their evidence? | S1 if evidence is absent, S4 if merely far away |
| 8 | Did checker strictness stay level or increase? | S3 finding, S1 if suppressions were added to force a merge |
| 9 | Is this an untyped-language project being force-typed? | Over-enforcement — flag the reviewer's own zeal; see `gradual-languages.md` |

## Reporting Format

Report findings as: severity, location, the ambiguous expression, the concrete fix.

> **S2 — `app/Models/Location.php:44`** — `$location->preview ?? $location->banner ?? $location->thumbnail` repeated at 3 call sites; each caller re-derives the image policy and gets a nullable back. Fix: add `Location::primaryImage(): Image` (throwing) or `primaryImageOrDefault(): Image`, replace the chains, and type the three properties via casts + `@property` annotations.

Rules for the report:

- Quote the exact expression; do not paraphrase.
- Every finding names a concrete fix with the target type, not just "add types".
- Acknowledge justified escape hatches ("`mixed` here is fine — serializer boundary, documented") so the review reads as calibrated, not dogmatic.
- If the codebase is untyped by choice, the only typing note is the single scoped suggestion allowed by `gradual-languages.md`.
