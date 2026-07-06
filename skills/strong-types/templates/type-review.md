# Type-Strictness Review — <change name>

Reviewed against the strong-types skill. Findings ordered by severity; see `references/review-rubric.md` for definitions.

## Verdict

<One paragraph: is the change acceptably unambiguous, and what must change before merge.>

## Findings

### S1 — Will fail at runtime

- **<file:line>** — `<exact ambiguous expression>`
  Fix: <concrete fix with the target type>

### S2 — Will fail on change

- **<file:line>** — `<exact ambiguous expression>`
  Fix: <concrete fix with the target type>

### S3 — Costs readers

- **<file:line>** — <finding>
  Fix: <concrete fix>

### S4 — Style

- <optional; drop this section when S1/S2 findings exist>

## Justified Escape Hatches

- **<file:line>** — `<expression>` — accepted because <serializer boundary / documented invariant / test fixture>.

## Type Ambiguity Gate

| Gate | Status | Note |
|---|---|---|
| Signatures | pass / fail | |
| Escape hatches | pass / fail | |
| Boundaries | pass / fail | |
| Nullability | pass / fail | |
| States | pass / fail | |
| Casts | pass / fail | |
| Suppressions | pass / fail | |
| Strictness | pass / fail | |
| Data shapes | pass / fail | |
| Proportionality | pass / n/a | untyped-language code not force-typed |

## Follow-Ups (out of scope for this diff)

- <pre-existing ambiguity worth a separate task, e.g. schema normalization behind a fallback chain>
