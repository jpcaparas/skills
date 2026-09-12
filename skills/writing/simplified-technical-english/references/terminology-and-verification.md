# Terminology and verification

Use this reference for every rewrite or audit. It controls source authority, dictionary decisions, technical terms, and claims about the result.

## Evidence modes

### Reference-backed review

Use this mode only when the task has:

- the applicable official ASD-STE100 issue or an authorized local copy
- enough of its dictionary and rule explanations to check every material decision
- the organization’s governed terminology for technical nouns, technical verbs, abbreviations, and preferred forms
- applicable publication, safety, regulatory, and legal directives
- technical review for meaning-sensitive decisions

Report the exact issue and terminology revision used. Do not call the result certified or ASD-approved.

### Scoped reference-backed review

Use this mode when a supplied profile, checklist, or approved local rule set explicitly covers every decision in a declared scope.

The source can disclaim completeness for full ASD-STE100 review and still be complete for its named subset. Apply all supplied vocabulary, terminology, counting, and structure decisions within that subset. Report:

- the profile and terminology revision used
- the checks included in the scope
- the checks outside the scope
- any source decision that the supplied materials do not settle

Call the result “checked against the supplied scoped profile.” Do not extend the result to full-standard conformance.

### Issue 9-oriented rewrite

Use this mode when one or more required sources are missing.

Apply the verified structural principles, produce useful candidate text, and list what remains unverified:

- general-word approval
- approved meaning
- approved part of speech
- verb form
- technical noun or technical verb status
- abbreviation or preferred-term status
- external directive conflict

Do not silently present provisional word choices as dictionary-approved.

## Source precedence

Resolve sources in this order for the decision they own:

1. technical source of truth for facts and product behavior
2. applicable law, safety rule, regulatory directive, contract, or publication specification
3. official ASD-STE100 issue for controlled-language rules and dictionary decisions
4. governed organization or project terminology for technical terms
5. source document for wording that another authority has not settled

Higher authority for one decision does not automatically own another. A company glossary can define a component name but cannot change an engineering limit.

If sources conflict, stop that decision and report the exact conflict.

## Term ledger

Create a row for every term that affects meaning or consistency:

| Source term | Concept | Status | Evidence | Output term | Notes |
|---|---|---|---|---|---|
| source wording | one technical concept | verified general word / technical noun / technical verb / protected literal / unresolved | dictionary entry, drawing, glossary, termbase, directive | selected term | meaning, part of speech, exception |

Keep one term for one concept and one concept for one term when the governed sources permit it.

## General approved words

Verify all of these together:

- the word appears as approved in the applicable dictionary
- the intended meaning matches the approved meaning
- the part of speech matches
- the form is permitted
- the sentence construction uses the word correctly

A familiar word can still be unapproved in a particular meaning or part of speech. Do not infer approval from frequency or simplicity.

Do not recreate the dictionary from memory, a third-party list, or a prior issue.

## Technical nouns

A technical noun names a subject-field concept. Evidence can include:

- official parts information
- engineering drawings
- approved company or project glossaries
- terminology databases
- applicable technical specifications

An otherwise unapproved word can occur inside a governed technical noun. This does not make the word generally approved.

For each technical noun:

- verify the named concept
- verify the authoritative form
- keep it consistent
- prefer a short, easy-to-understand governed form when the terminology owner permits one
- preserve product names, part numbers, labels, and identifiers

Do not use a technical noun as a verb merely because standard English permits it.

## Technical verbs

A technical verb names a subject-field action or process. Verify it through the same governed terminology sources.

For each technical verb:

- verify the action or process
- verify that the context and subject field permit it
- preserve its approved form
- do not use it as a noun
- do not promote a vague general verb to technical status

## Multi-word technical terms

Issue 9 normally limits multi-word nouns to three words but gives rules for longer official technical nouns.

When an official term exceeds three words:

1. preserve its full authoritative form at the required introduction point
2. use an approved short form, abbreviation, or other governed reference only when the source permits it
3. use hyphens only when they correctly connect directly related words
4. do not invent a shorter alias

If the publication directive requires the full long term at every use, record the exception.

## Abbreviations and spelling

ASD-STE100 does not govern an organization’s abbreviation system. Use the applicable project or publication directive.

Use American English spelling unless an applicable official directive requires another spelling. Do not change a product label, quoted string, command, or identifier to match spelling policy.

## Verification record

Record:

- standard issue and date
- rule sections checked
- dictionary source available or missing
- terminology source and revision
- publication and safety directives
- protected literals compared
- automated diagnostic version, if used
- confirmed findings
- unresolved terms and exceptions
- technical, editorial, safety, legal, and final reviewers as applicable

This record supports internal review. It is not an ASD certification procedure.

## Claim language

Permitted when accurate:

- candidate STE rewrite
- Issue 9-oriented rewrite
- checked against the supplied scoped profile
- reviewed against the supplied Issue 9 materials
- checked for the listed Issue 9 constraints
- vocabulary verification incomplete

Do not claim:

- certified ASD-STE100
- ASD-approved
- officially endorsed
- guaranteed compliant
- automatically converted to STE

ASD and the STEMG state that tools, including AI tools, are optional aids and cannot replace the writer or the standard.
