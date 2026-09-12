# Quality gates

Use these gates before handing off a draft, rewrite, review, or adaptation. Apply only the gates that fit the job, but never skip fidelity when source material exists.

## Gate 1: Fidelity

Compare the final prose with the source and preservation ledger.

Pass when:

- names, dates, numbers, units, comparisons, and causal direction match
- quotations remain exact and attributed
- citations still support the nearby claim
- commands, code, paths, flags, identifiers, configuration, and other machine-readable constructs are unchanged; route any requested correction to the appropriate non-writing workflow
- conditions, exceptions, and failure modes survive
- uncertainty has not become confidence
- personal experience has not been invented or reassigned
- omitted material was deliberately removed rather than accidentally lost

Unsupported source hype is not protected merely because it appeared in the draft. Preserve the underlying intended claim only when the source can support it; otherwise remove it or report the evidence gap.

For high-risk work, perform a literal diff or extract protected tokens before and after the edit.

## Gate 2: Logic and evidence

Pass when:

- the thesis, task, or decision is visible where the genre expects it
- each paragraph has one job
- each material claim has evidence, reasoning, or an honest qualifier
- attribution is named and inspectable where required
- cause, correlation, forecast, and opinion remain distinct
- transitions express real relationships
- counterarguments are represented fairly
- the ending follows from the body rather than announcing a broader conclusion

If a claim cannot be supported, narrow, source, or remove it. Do not write around the gap with confidence language.

## Gate 3: Clarity and cadence

Pass when:

- sentences can be parsed on first read
- actors, actions, conditions, and consequences are easy to locate
- technical terms are defined for the intended reader and then used consistently
- paragraph and sentence lengths follow the material rather than a template
- connective tissue remains where the logic needs it
- repeated openings, triads, fragments, or punctuation patterns are deliberate
- the opening, densest paragraph, and ending read aloud without accidental stumbles

## Gate 4: Voice and humanisation

Pass when:

- the writer's stance, source of authority, and limits are legible
- specific detail displaces generic mood or praise where evidence allows
- formulaic frames no longer carry the argument
- remove-by-default wrappers are gone unless the genre requires them
- rewrite-by-default phrases expose their actor, mechanism, evidence, comparison, or consequence
- rejected phrases were not replaced with equally vague synonyms
- a diagnostic match was never treated as proof of authorship
- dialect, second-language identity, accessibility choices, and intentional rhetoric remain intact
- no fake typo, slang, anecdote, emotion, or first-person claim was added
- high-signal source lines survived unless there was a clear reason to change them

When a substantial draft was scanned, rerun it after the last substantive edit. Review every remove- and rewrite-labelled candidate when the writing contract includes an explicit formulaic-language ban, and record any deliberate exception. Use `--gate` only for the conservative multi-pattern cluster check.

## Gate 5: Genre and reader task

Pass when:

- the opening gives this reader the right orientation
- headings promise useful content rather than label document furniture
- lists, tables, and paragraphs match the information shape
- the level of explanation suits the reader's knowledge
- the length reflects the material, not filler or arbitrary compression
- the ending performs the required job: verification, recommendation, request, action, implication, or outward turn
- the deliverable looks native to its channel

Use the genre-specific checks in `references/genre-modes.md`.

## Gate 6: Mechanics and accessibility

Pass when:

- spelling, grammar, punctuation, capitalisation, and locale are consistent
- headings follow the chosen house style
- abbreviations are expanded when the reader needs them
- links have meaningful text and resolve when verification is in scope
- instructions do not depend on visual position or colour alone
- tables have real comparative value and remain readable
- UI text is concise without hiding consequence or recovery
- quotations, code, and data are formatted without corruption

## Gate 7: Review integrity

Apply this gate when the job is critique rather than rewrite.

Pass when:

- findings are ranked by reader impact
- each finding cites a precise passage or observable pattern
- explanation distinguishes defect, risk, and preference
- suggested changes preserve the source's facts and purpose
- examples are labelled as examples rather than silent replacements
- praise identifies what works and why, so later revision protects it
- the review does not claim external facts it did not verify

## Gate 8: Final proof

Run last.

1. Read the first screen without context. Does it establish the right contract?
2. Read one dense middle section. Can the reader follow the reasoning or task?
3. Read the ending. Does it add the right final move rather than recap by habit?
4. Compare protected literals and claims with the source.
5. Check the output format and requested locale.
6. Confirm that all diagnostics were rerun after the last real rewrite.

## Severity and release decisions

| Finding | Default decision |
|---|---|
| Fidelity breach | block handoff |
| Invented fact, quote, citation, proof, or experience | block handoff |
| Material logical contradiction | block handoff |
| Unsafe or misleading instruction | block handoff |
| Unresolved high-confidence formula cluster that obscures meaning | revise or record deliberate exception |
| Mechanical error that changes meaning | block handoff |
| Minor style preference | fix only if it clearly improves the piece |

## Stop condition

Stop when:

- every applicable gate passes
- the requested outcome is present
- protected material is intact
- no known critical defect remains
- further edits would be taste-equivalent or would trade one strength for another

An endless polish loop is a quality failure. Save the strongest passing version.
