# Review and reporting

Use this reference when the user requests an audit, findings, reviewer handoff, or evidence record.

## Audit boundary

An audit diagnoses the supplied text. It does not silently replace the whole document.

Confirm:

- selected text
- text type
- governing issue and terminology sources
- whether the audit covers language only or also checks publication directives
- whether local correction examples are permitted

Do not perform engineering, safety, legal, or regulatory validation through language review.

## Finding classes

### Confirmed

Use when the available source proves the violation or mismatch.

Examples:

- procedure sentence exceeds the verified word limit
- semicolon occurs in natural-language text
- a procedure uses passive voice
- one step contains independent instructions
- an approved word uses the wrong verified part of speech
- a project term differs from the governed terminology entry

### Candidate

Use when a deterministic or linguistic signal requires human judgment.

Examples:

- probable passive voice
- possible phrasal verb
- possible `-ing` verb form
- dense multi-word noun
- pronoun with a possibly unclear referent

### Unresolved

Use when the decision requires missing technical or authoritative evidence.

Examples:

- whether a term is a governed technical noun
- whether two actions occur simultaneously
- what `it` refers to
- whether mandated safety wording can change
- whether a later issue supersedes the supplied dictionary entry

## Severity

| Severity | Use when |
|---|---|
| Blocker | A rewrite would guess technical meaning, risk, legal force, or a required source |
| High | A confirmed language issue can change action, condition, sequence, threshold, or consequence |
| Medium | A confirmed rule issue materially reduces controlled-language consistency or clarity |
| Low | A localized issue has limited effect and a clear correction |
| Information | Evidence boundary, permitted exception, or reviewer note |

Do not assign engineering risk from language alone.

## Finding format

Each finding includes:

- identifier
- source location
- text type
- classification: confirmed, candidate, or unresolved
- severity
- rule section or governing source
- exact source excerpt, kept short
- explanation
- local correction example when authorized
- evidence needed or owner

Do not paste large portions of the copyrighted standard into the report. Paraphrase the applicable requirement and cite the official source.

## Audit output

Lead with the result:

1. scope and evidence mode
2. blocker count and highest-severity findings
3. findings in source order or severity order
4. terminology and protected-literal checks
5. unresolved questions and owners
6. verification record

If the user asks for findings only, do not append a complete rewritten document.

## Rewrite plus report

When the user requests both:

1. give the rewritten text
2. give only material findings and exceptions
3. report the evidence boundary

Avoid a line-by-line edit log when it adds no review value.

## Acceptance gate

A report is complete when:

- every selected block was classified
- every material issue is confirmed, candidate, or unresolved
- every blocker has a focused question or owner
- the report distinguishes language review from technical approval
- protected literals and semantic invariants were compared
- no certification or endorsement claim appears

Use `templates/rewrite-report.md` for a durable record.

## See also

- `references/terminology-and-verification.md` — evidence modes and claim language
- `references/procedures-and-safety.md` — procedure and safety checks
- `references/descriptive-writing.md` — description checks
