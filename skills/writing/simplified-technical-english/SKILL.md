---
name: simplified-technical-english
description: "Rewrite or audit ASD-STE100 procedures, descriptions, and safety instructions while preserving technical meaning and exact literals."
compatibility: "Core instructions are portable. The optional surface scanner requires Python 3.11 or newer."
metadata:
  version: "1.0.0"
references:
  - procedures-and-safety
  - descriptive-writing
  - terminology-and-verification
  - review-and-reporting
  - research-notes
  - gotchas
---

# Simplified Technical English

Rewrite selected technical text into a precise candidate STE form, or audit it against the applicable ASD-STE100 constraints.

## Route the request

Choose the job and evidence mode before changing text.

| Decision | Branch |
|---|---|
| User asks for replacement text | Rewrite |
| User asks for findings only | Audit; do not return a full replacement |
| Instructions, work steps, maintenance tasks, or safety text | Procedure/safety |
| System, component, theory-of-operation, report, or explanatory text | Description |
| Both text types occur | Segment the source and apply each branch separately |
| All sources and review obligations in the reference-backed definition are available | Full reference-backed review |
| A supplied rule profile and governed terminology cover a declared subset of checks | Scoped reference-backed review |
| The standard, dictionary, or governed terminology is incomplete | Issue 9-oriented rewrite with explicit unverified items |

Map a request for “strict,” “fully compliant,” or “certified” output to reference-backed review. A bounded profile can support strict checking only for its declared scope; it cannot support a whole-standard claim. If the sources required for the requested scope are absent, say that strict verification is blocked. You may also provide a separately labelled provisional rewrite when it is safe and useful.

Do not use this skill for ordinary tone changes, general simplification, translation, language lessons, engineering or legal validation, or edits to source code and identifiers.

## Required context

Read only the references that the selected text needs:

- Read `references/terminology-and-verification.md` for every rewrite or audit; use it to select the evidence mode, govern technical terms, and bound claims.
- Read `references/procedures-and-safety.md` for procedures, work steps, notes, warnings, or cautions; use it to transform commands, conditions, sequence, and risk statements.
- Read `references/descriptive-writing.md` for explanatory or descriptive text; use it to control information order, voice, sentences, and paragraphs.
- Read `references/review-and-reporting.md` when the user requests findings, an audit trail, or a conformance report; use it to separate confirmed violations from unresolved decisions.
- Read `references/gotchas.md` when source text contains mandated safety wording, mixed content, ambiguous references, unusually long technical terms, or conflicting directives.
- Read `references/research-notes.md` only when source provenance, current issue status, copyright, or maintenance of this skill is in scope.

## Operating workflow

### 1. Establish the rewrite contract

Identify:

- the exact selected text and text outside scope
- procedure, description, safety instruction, or mixed content
- the applicable standard issue, publication specification, company style guide, and terminology source
- whether the user wants a rewrite, an audit, or both
- whether the result is fully reference-backed, scoped reference-backed, or Issue 9-oriented
- the responsible technical reviewer when the text affects safety, legality, or product behavior

Issue 9, dated 15 January 2025, is the current official issue in the evidence for this release. Verify current status when the user asks for the latest issue or when later material is supplied.

**Complete when:** scope, text type, evidence mode, governing sources, output form, and review owner are known or explicitly marked unavailable.

### 2. Build a preservation ledger

Record the source elements that must not change:

- technical facts, causal direction, conditions, exceptions, uncertainty, and sequence
- prohibitions, permissions, required actions, warning level, hazard, mitigation, and consequence
- numbers, units, tolerances, ranges, limits, comparison operators, and polarity
- part numbers, reference designators, product names, labels, proper nouns, abbreviations, and approved technical terms
- code fences, inline code, commands, paths, URLs, endpoints, identifiers, schema keys, tags, placeholders, citations, and quoted regulated text
- headings, markers, and text outside the selected boundary

Do not “simplify” a protected term or literal. If a safety or legal sentence is controlled by another authority, preserve it or route it for authorized review.

**Complete when:** every high-consequence fact and exact literal has a source value against which the result can be compared.

### 3. Segment and classify

Divide mixed documents into the smallest stable blocks:

- procedural steps
- descriptive paragraphs
- safety instructions
- notes
- tables and labels
- protected machine-readable or quoted material

Do not apply one text type’s rules to another. A note in a procedure gives information; it does not hide an instruction. A description explains; it does not become a command.

**Complete when:** each selected block has one text type and protected blocks are excluded from natural-language rewriting.

### 4. Resolve technical meaning before language

Build a term ledger with one status for each material term:

- verified approved general word, meaning, and part of speech
- governed technical noun
- governed technical verb
- proper noun, identifier, abbreviation, or protected label
- unverified candidate that needs the official dictionary or a terminology owner

Keep one approved term for one concept. Do not promote an unfamiliar word to a technical term because it sounds specialized. Do not guess what a pronoun, threshold, action, or component means.

When ambiguity changes the action, target, condition, sequence, or risk, ask a focused question or record the unresolved alternatives before producing a reference-backed result.

**Complete when:** every consequential term and ambiguous reference is verified, protected, or reported as unresolved.

### 5. Rewrite the structure

Transform meaning units before replacing individual words:

1. Put information in the order the reader must use it.
2. Split independent instructions and topics. Count coordinated verbs and compound required-state checks separately; do not hide two actions inside one `make sure` command.
3. Make actors, actions, objects, conditions, and results explicit.
4. Replace nominalized actions with direct verbs when the governed vocabulary permits it.
5. Remove avoidable ambiguity, hidden coordination, omitted words, and unnecessary synonym variation.
6. Use a vertical list when one sentence would carry several related items or conditions.

Use a different sentence construction when a word-for-word replacement cannot preserve clear meaning.

**Complete when:** the result has explicit logic, stable terminology, and no sentence that still carries unrelated work.

### 6. Apply the text-type rules

For procedures and safety instructions, apply `references/procedures-and-safety.md`.

For descriptions, apply `references/descriptive-writing.md`.

For mixed text, complete each branch independently and then restore the original document order.

Shared surface requirements include:

- approved vocabulary only in its verified meaning and part of speech
- governed technical nouns and technical verbs
- short, complete sentences without contractions
- active voice, except a permitted descriptive passive when the agent is unknown
- controlled verb forms and tightly limited `-ing` forms
- no semicolons
- consistent terminology and wording
- American English spelling unless an applicable directive requires another spelling

These shared requirements are not a substitute for checking the official Issue 9 dictionary and full rule explanations.

**Complete when:** every block passes its branch checklist or has a precise exception with an owner.

### 7. Verify rather than certify

Compare the result with the preservation ledger. Check:

1. meaning, conditions, negation, thresholds, sequence, and risk
2. selected-text boundaries and protected literals
3. text type, voice, sentence function, word count, and paragraph structure
4. terminology consistency
5. approved word, meaning, part of speech, and verb form against the available Issue 9 material
6. project terminology against the governed glossary or termbase
7. conflicts with publication, safety, legal, or regulatory directives

For a file, the optional scanner can find surface candidates:

```bash
python3 scripts/analyze_ste_surface.py --text-type procedure path/to/text.md
python3 scripts/analyze_ste_surface.py --text-type description --format json path/to/text.md
```

The scanner does not contain the ASD-STE100 dictionary, does not decide technical meaning, and does not establish conformance. Judge every finding in context.

**Complete when:** each applicable check has evidence, each exception has an owner, and no unverified item is presented as verified.

### 8. Deliver the result

For a rewrite, lead with the complete rewritten selection. Preserve surrounding document structure when the user supplied a file or selection markers.

Then give a compact verification note:

- mode: full reference-backed review, scoped reference-backed review, or Issue 9-oriented rewrite
- standard issue and terminology source used
- protected literals checked
- unresolved terminology, ambiguity, or directive conflicts
- human review required for technical, safety, legal, or organizational approval

For an audit, use the report contract in `references/review-and-reporting.md` and do not silently replace the source.

Use “candidate STE rewrite,” “Issue 9-oriented rewrite,” “checked against the supplied scoped profile,” or “checked against the supplied Issue 9 materials.” State the exact scope of a bounded profile. Never claim ASD certification, endorsement, authorization, official approval, or guaranteed compliance.

**Complete when:** the requested artifact is present, the evidence boundary is explicit, and the result does not overstate its authority.

## Output contract

Default rewrite output:

1. rewritten text
2. short verification note
3. unresolved questions only when they affect correctness

Use `templates/rewrite-report.md` when the user wants an audit trail, reviewer handoff, or batch record. Keep ordinary responses lighter.

## Non-negotiables

1. Preserve technical meaning before improving language.
2. Preserve negation, conditions, thresholds, sequence, warning level, mitigation, and consequence exactly.
3. Never invent an approved dictionary status, meaning, part of speech, technical noun, or technical verb.
4. Never alter code, commands, identifiers, paths, URLs, tags, placeholders, or other protected literals.
5. Never hide an instruction in a note or turn descriptive information into an unsupported command.
6. Never claim certification, ASD approval, or guaranteed compliance.
7. Never redistribute or reconstruct the official standard, dictionary, examples, logo, or cover art in the output.
8. Stop a reference-backed rewrite when unresolved ambiguity could change safety, legality, or product behavior.
