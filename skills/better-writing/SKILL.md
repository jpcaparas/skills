---
name: better-writing
description: "Draft, rewrite, review, humanise, or adapt prose while preserving facts, intent, voice, and uncertainty. Use for technical, product, editorial, marketing, or personal writing, including stiff or AI-like drafts. Skip code-only tasks."
compatibility: "Core instructions are portable. Optional diagnostics and package checks require Python 3.10+."
metadata:
  version: "2.3.0"
references:
  - operating-contract
  - revision-pass-stack
  - natural-structure-and-digestibility
  - foundations
  - voice-and-rhythm
  - punctuation-and-sentence-flow
  - genericity-and-stiffness
  - ai-isms-and-humanisation
  - formulaic-language-catalogue
  - genre-modes
  - style-bundles
  - quality-gates
  - research-notes
  - gotchas
---

# Better writing

Make prose clear, faithful, specific, well-shaped, and recognisably owned by its writer.

## Route the request

Choose the job before touching the prose.

| Job | Use it when | Primary references |
|---|---|---|
| Draft | The user needs new prose from notes, evidence, or a brief | `references/operating-contract.md`, `references/genre-modes.md` |
| Rewrite | A draft exists and may be restructured or recast | `references/revision-pass-stack.md`, `references/quality-gates.md` |
| Line edit | The shape works; sentences need clarity, rhythm, or economy | `references/foundations.md`, `references/voice-and-rhythm.md` |
| Review | The user wants diagnosis or comments, not a rewritten artefact | `references/quality-gates.md` |
| Humanise | The prose feels generic, machine-smooth, formulaic, or unlike its author | `references/ai-isms-and-humanisation.md`, `references/genericity-and-stiffness.md`; add `references/formulaic-language-catalogue.md` for explicit avoidance or dense formulae |
| Adapt | The substance should stay while audience, genre, channel, length, or voice changes | `references/genre-modes.md`, `references/style-bundles.md` |

Mixed requests can use more than one job. Keep scope clean: if a request combines a code fix with an error-message rewrite, this skill may revise the user-facing words but does not edit the surrounding source, syntax, or code behaviour. Never rename, rewrite, or reinterpret code constructs to satisfy a style or diction rule. In mixed documentation, edit only the natural-language prose and preserve machine-readable material exactly.

For an explicit request to remove, replace, limit, or standardise em dashes, semicolons, or colons, read `references/punctuation-and-sentence-flow.md`. Load it conditionally; ordinary line editing and humanisation do not imply a punctuation ban.

Use another workflow for code-only implementation, standalone fact-checking, or authorship classification. This skill may rewrite prose produced alongside those tasks, but it does not perform them.

## Operating workflow

### 1. Establish the writing contract

Infer what the supplied context already settles. Identify:

- reader, deliverable, and desired outcome
- source material and factual authority
- required length, format, locale, house style, and deadline
- whether the user wants a draft, rewrite, review, humanisation pass, or adaptation
- how much change is allowed

For an existing draft, build a preservation ledger before editing. Protect facts, numbers, dates, names, quotations, citations, commands, paths, API identifiers, legal or technical terms, explicit uncertainty, and lines that carry the writer's voice.

Ask only when a missing choice would materially change the result. Never invent evidence, experience, approval, customer language, or confidence the source does not contain.

Do not treat unsupported praise or marketing posture as a factual invariant. If removing vague claims leaves too little to write, surface the evidence gap or ask for the missing mechanism instead of rearranging the same abstractions.

Read `references/operating-contract.md` when the source is sensitive, highly constrained, collaborative, or likely to lose important detail.

**Complete when:** the reader, outcome, edit freedom, source authority, and protected material are known or explicitly marked unknown.

### 2. Diagnose before rewriting

Name the failure at the right scale:

- whole-piece: wrong genre, audience, order, thesis, or scope
- section: missing step, evidence, turn, or decision
- paragraph: mixed jobs, buried point, repetition, weak transition
- sentence: unclear actor, abstraction, drag, monotony, or false emphasis
- surface: grammar, spelling, punctuation, formatting, or house style

Preserve what already works. A good edit is not a demonstration that every sentence can be changed.

**Complete when:** the smallest responsible layer and the draft's strongest material are both identified.

### 3. Fix shape before style

Choose the page shape in `references/genre-modes.md`. Give each section and paragraph one job. Put the main point where that genre expects it. Order evidence so the reader never has to guess why it is present.

Read `references/natural-structure-and-digestibility.md` when the request calls for a substantial structural recast, a more natural flow, or repair of dense, wall-of-text, or over-chunked prose. Use its worked transformations to split at changes of job, not at arbitrary lengths.

For review-only work, stop short of rewriting: report the diagnosis, cite exact passages, rank issues by reader impact, and offer a rewrite only as a clearly labelled example.

**Complete when:** the opening establishes the right contract, the middle advances it without echoing itself, and the ending performs the genre's real closing task.

### 4. Run two clarity passes

Use `references/revision-pass-stack.md`.

1. **Paragraph pass:** one job per paragraph, visible logic, no repeated claim, evidence beside the claim it supports.
2. **Sentence pass:** clear actor and action, concrete nouns and verbs, related words together, honest qualifications, informative emphasis.

Do not compress every sentence. Restore connective tissue when the page starts to read like chopped notes. When a long passage needs reshaping, choose paragraphs, lists, headings, or tables from the information's real shape; formatting cannot replace reasoning.

When punctuation is the edit target, classify the relation before changing the mark. A colon fulfils a promise, a semicolon balances close independent clauses, and a conjunction or subordinate clause should name logic that punctuation would otherwise leave implicit. Protect literal punctuation in code, URLs, times, ratios, quotations, labels, and configuration.

**Complete when:** a reader can follow the argument or procedure on the first read without losing the draft's meaning or cadence.

### 5. Restore voice and specificity

Use `references/voice-and-rhythm.md` for stance, cadence, sentence movement, and read-aloud repair. Use `references/style-bundles.md` to calibrate a voice from samples or declared traits without imitating a living writer's signature.

Human signal comes from judgement, selection, detail, and position—not fake typos, random slang, decorative swearing, invented anecdotes, or forced informality.

**Complete when:** the prose has a discernible point of view, sentence movement suits the thought, and the writer's high-signal details remain intact.

### 6. Run the formulaic-language and humanisation pass

Run a light avoidance check on every prose deliverable. Do not introduce assistant residue, empty ceremony, canned significance, unsupported benefit language, or a formula that hides the actor, mechanism, evidence, or consequence.

Read `references/ai-isms-and-humanisation.md` and `references/formulaic-language-catalogue.md` when the user asks to remove AI-like words or phrases, ban formulaic diction, make prose less robotic, or when a draft shows generic authority, excessive symmetry, service tone, or repeated rhetorical frames.

Apply the catalogue's action levels:

- remove wrappers and empty stage directions
- rewrite canned semantic frames from supported meaning, even when they occur once
- review ordinary words and structural signals in context or clusters
- protect literal, technical, legal, measured, quoted, and writer-owned uses

Never perform a synonym swap to satisfy an avoidance rule. This applies across the catalogue, not only to individual watch words. `Bridge the gap` does not become `close the divide`; identify what is missing and what action changes it. `Marks a significant shift` does not become `signals a major transformation`; state the before and after. `Plays a critical role`, `unlocks value`, and `research shows` likewise need a supported action, result, or source. If the source lacks the necessary substance, delete, narrow, or query the claim.

If a substantial draft exists as a file, run:

```bash
python3 scripts/scan_aiisms.py path/to/draft.md
```

Use `--format json` for automation and `--gate` only as a conservative multi-pattern cluster gate. A normal scan already surfaces single remove-, rewrite-, and review-labelled matches. Judge those matches against their exceptions; the scanner cannot determine whether a use is exact, suitable for its genre, or evidence of authorship. Treat an em dash, polished sentence, or ordinary word as context—not proof.

Rewrite the thought, not just the flagged token. Preserve dialect, accessibility choices, second-language voice, quoted material, literal terminology, and intentional rhetoric.

**Complete when:** remove and rewrite rules are resolved or deliberately retained, review-only clusters have been judged in context, and the revision reads better by ordinary editorial standards—not merely less detectable.

### 7. Calibrate the deliverable

Apply the target genre, audience, locale, and house style. Check headings, lists, calls to action, examples, and ending shape. Keep formatting proportional to the material; not every paragraph wants a heading and not every thought wants a bullet.

**Complete when:** the artefact looks and sounds native to its destination without losing factual or personal identity.

### 8. Pass the quality gates and stop

Run the gates in `references/quality-gates.md`:

1. fidelity
2. logic and evidence
3. clarity and cadence
4. voice and humanisation
5. genre and mechanics
6. final proof

Compare the revision against the preservation ledger. Re-run deterministic diagnostics after the last substantive edit, not before it. Stop when every remaining change is merely different, not better.

**Complete when:** the deliverable passes every applicable gate, protected material matches the source, and no known critical issue remains.

## Output contract

Lead with the requested artefact or review outcome. Keep process notes brief unless the user asked for an edit log. When useful, report:

- important structural choices
- protected facts or literals
- unresolved factual questions
- deliberate exceptions to a diagnostic signal

Do not claim a passage was AI-written. Do not turn stylistic preference into an accusation.

## Quick reference

| Need | Read or run |
|---|---|
| Brief, preservation ledger, and edit freedom | `references/operating-contract.md` |
| Exact revision order and loopbacks | `references/revision-pass-stack.md` |
| Natural structure, paragraph architecture, and long-prose digestibility | `references/natural-structure-and-digestibility.md` |
| Grammar, clarity, and modern usage baseline | `references/foundations.md` |
| Cadence, stance, and voice repair | `references/voice-and-rhythm.md` |
| Em-dash replacement, semicolon and colon judgement, and sentence-flow repair | `references/punctuation-and-sentence-flow.md` |
| Generic, corporate, ceremonial, or inflated prose | `references/genericity-and-stiffness.md` |
| AI-like patterns, humanisation, false positives, and scanner use | `references/ai-isms-and-humanisation.md` |
| Contextual avoid rules, phrase families, natural rewrites, and protected uses | `references/formulaic-language-catalogue.md` |
| Docs, PRs, specs, memos, reports, essays, email, UI, and copy | `references/genre-modes.md` |
| Personal voice sheets and style calibration | `references/style-bundles.md` |
| Acceptance criteria and final proof | `references/quality-gates.md` |
| Research basis and limits | `references/research-notes.md` |
| Failure recovery | `references/gotchas.md` |

## Templates

- `templates/rewrite-worksheet.md` records the brief, preservation ledger, pass results, and final gates.
- `templates/personal-style-sheet.md` captures a writer's real habits from samples before revision smooths them away.

## Non-negotiables

1. Never improve style by changing the facts.
2. Never convert uncertainty into confidence without evidence.
3. Never invent personal experience, quotations, citations, proof, or customer language.
4. Never mimic a named writer's signature; translate the request into high-level traits.
5. Never use a phrase list or detector score as proof of authorship.
6. Never sand away dialect, accessibility, or second-language identity to make prose look statistically “human.”
7. Never satisfy a formulaic-language rule through synonym substitution alone.
8. Never keep editing after the applicable gates pass and the remaining options are taste-equivalent.
9. Never alter code, identifiers, selectors, configuration keys, or other machine-readable constructs; revise only the natural-language prose in scope.
