# Operating contract

Use this reference before drafting or editing when the work has meaningful constraints, source material, collaborators, or factual risk.

## 1. Define the job

Write a one-sentence contract:

> Create or revise **[deliverable]** for **[reader]** so they can **[outcome]**, using **[source authority]**, while preserving **[protected material]**.

The contract should answer five questions:

1. What is being made?
2. Who will read it?
3. What should change for that reader?
4. Which material is authoritative?
5. How much freedom does the edit have?

Infer answers that the prompt, draft, repository, or house style already supplies. Ask only when the missing answer would produce a materially different artefact.

## 2. Set edit freedom

| Level | Allowed work | Protected by default |
|---|---|---|
| Proofread | grammar, spelling, punctuation, formatting | wording, order, voice, claims |
| Line edit | sentence clarity, rhythm, concision, local transitions | argument, section order, factual content |
| Copy edit | consistency, usage, terminology, mechanics, local clarity | authorial position and substantive claims |
| Rewrite | sentences, paragraphs, order, openings, endings | intent, evidence, constraints, protected voice |
| Developmental edit | thesis, scope, structure, missing reasoning, genre | source truth, authorial purpose, explicit boundaries |
| Draft | create prose from supplied material | evidence limits, brief, reader, requested voice |
| Review | diagnose, rank, and explain | the source artefact itself unless edits are authorised |

When the user says “polish,” infer the narrowest level that solves the visible problem. Do not silently turn a proofread into a rewrite.

## 3. Build the preservation ledger

For an existing draft, record what must survive. Use the smallest ledger that protects the work.

### Exact literals

Preserve byte-for-byte unless the user authorises a change:

- commands, code, configuration, paths, filenames, flags, and environment variables
- API names, schema fields, identifiers, product names, and version strings
- quotations and attributed wording
- URLs and citation destinations
- legally prescribed or regulated language

If an exact literal appears wrong, flag it. Do not “correct” it from memory.

### Factual invariants

Preserve meaning exactly:

- names, dates, quantities, units, comparisons, and causal direction
- who did what, when, and with what result
- scope words such as `all`, `some`, `first`, `only`, and `at least`
- conditions, exceptions, failure modes, and limitations
- source attribution and confidence

### Epistemic invariants

Keep the difference between:

- observed and inferred
- possible, likely, and certain
- correlation and causation
- proposal and decision
- estimate and measurement
- first-hand experience and second-hand report

An edit that sounds firmer but outruns the evidence is not an improvement.

### Voice anchors

Protect lines that carry useful identity:

- an odd but accurate metaphor
- a precise domain term
- a candid admission or reversal
- a sentence with characteristic rhythm
- a culturally or regionally meaningful expression
- a deliberate fragment, aside, or joke that works

Mark these before line editing. Otherwise a consistency pass may erase them.

## 4. Establish source authority

Use this order unless the user states another:

1. user-supplied facts and approved source material
2. verified primary sources
3. repository or organisation policy
4. established house style
5. general editorial judgement

Do not use prose revision as an excuse to add claims. If current facts, legal accuracy, medical accuracy, or external citations need verification, verify them through the appropriate research process or mark the limitation. This skill does not turn memory into evidence.

## 5. Capture the audience contract

Avoid demographic caricatures. Define the reader through their task:

- What do they already know?
- What are they trying to decide, understand, feel, or finish?
- What can they safely skip?
- Which objection, risk, or uncertainty will block them?
- What vocabulary do they already use?

For accessibility, prefer explicit relationships, informative link text, descriptive headings, and instructions that do not depend on colour, position, or insider knowledge alone.

## 6. Choose the working artefact

For a small edit, work directly.

For substantial or high-risk work, use `templates/rewrite-worksheet.md` to record:

- the contract
- preservation ledger
- diagnosis
- pass results
- unresolved questions
- final gate evidence

Keep one prose owner. Parallel reviewers may return diagnostics, but overlapping rewrites make voice, facts, and edit intent hard to reconcile.

## Completion check

Before revision begins, confirm:

- the job and edit freedom are explicit
- the source of truth is known
- protected literals, facts, uncertainty, and voice anchors are recorded
- missing facts remain missing rather than invented
- the reader is defined by a real need

If one of these is unknown but non-blocking, label the assumption. If it could reverse the result, ask before writing.
