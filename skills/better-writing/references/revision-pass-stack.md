# Revision pass stack

Use this reference for a reliable edit order. Each pass has one job, a completion test, and a loopback. Do not make every pass equally heavy; a clean draft may need only one or two.

## Pass 0: Preserve and diagnose

Before rewriting:

- establish edit freedom and source authority
- record protected literals, facts, uncertainty, citations, and voice anchors
- identify the reader's desired outcome
- name the failure at whole-piece, section, paragraph, sentence, or surface level
- mark the strongest passage so revision does not flatten it

Use `references/operating-contract.md` for high-risk or constrained work.

**Pass when:** you can say what must change and what must not.

## Pass 1: Whole-piece shape

Choose the genre in `references/genre-modes.md`, then inspect:

- opening contract: does the reader know where the piece is taking them?
- thesis or task: is the central job visible where this genre expects it?
- section order: does each section create the need for the next?
- scope: does every part belong?
- ending: does it decide, verify, ask, invite, or turn outward as required?

Make a reverse outline: one short line describing what each paragraph does. Reorder, merge, or cut before polishing sentences.

For a substantial recast, use the worked cross-genre transformations in `references/natural-structure-and-digestibility.md`. They show how to rank material by the reader's next question without forcing every genre into a news lead.

**Pass when:** the reverse outline forms a coherent sequence with no duplicate jobs or missing bridge.

## Pass 2: Paragraph architecture

Give each paragraph one governing job.

- move the point nearer the front unless suspense or scene has earned delay
- keep evidence beside the claim it supports
- split paragraphs that mix unrelated argument, evidence, scene, and aside
- merge fragments that artificially break one thought into several blocks
- cut echo paragraphs and miniature conclusions
- replace transition labels with the relationship itself: cause, contrast, sequence, example, or consequence

When the source is a wall of text or has been split into fragments, use `references/natural-structure-and-digestibility.md` to choose the breakpoints and display form. Paragraph length is a review signal; the governing job decides whether to split or merge.

Useful questions:

- What would be lost if this paragraph disappeared?
- Does its first or second sentence explain why it exists?
- Does its last sentence move forward rather than repeat the opening?
- Is the transition logical, or merely smooth?

**Pass when:** every paragraph has one nameable job and advances the piece.

## Pass 3: Sentence clarity

Make the sentence easy to parse without lowering its precision.

- keep actor, action, and object within sight of one another
- turn noun-heavy actions back into verbs where that shortens the path
- replace abstract setup with the claim it postpones
- keep conditions and exceptions attached to the rule they qualify
- place the most informative material where the sentence can land on it
- use positive form when it clarifies, but keep negation when the contrast itself matters
- remove duplicated intensifiers, empty preambles, and throat-clearing
- preserve exact technical terms instead of “simplifying” them into vagueness

Read `references/foundations.md` for grammar and usage decisions.

**Pass when:** the sentence reads correctly on the first attempt and means exactly what the source meant.

## Pass 4: Evidence and epistemics

Compare the prose with the source, not with memory.

- verify names, dates, quantities, units, quotations, and causal direction
- keep citations attached to the claims they support
- distinguish observation, inference, estimate, prediction, and opinion
- replace vague authority with a named source or remove the borrowed authority
- remove proof words such as `clearly`, `obviously`, and `undeniably` when the evidence does not carry them
- preserve `may`, `likely`, `could`, and other qualifications when they are doing real epistemic work

**Pass when:** every factual claim has the right source, scope, and confidence.

## Pass 5: Voice and cadence

Run this pass after clarity so voice does not hide structural trouble.

- reconnect adjacent sentences when one thought has been chopped apart
- vary sentence length and architecture in response to meaning
- use contractions where they suit the writer and genre
- restore stance: who knows this, from what seat, and with what limit?
- keep a useful aside, fragment, reversal, or joke when it earns its space
- remove sentences that only announce importance

Read `references/voice-and-rhythm.md`.

**Pass when:** the paragraph can be read aloud without mechanical resets, accidental monotony, or borrowed performance.

## Pass 6: Genericity and humanisation

Run this pass when the draft sounds interchangeable, machine-smooth, ceremonious, or over-produced.

- replace praise words with mechanisms, evidence, or consequences
- cut service tone, generic authority, false suspense, tidy binaries, and self-summary
- inspect repeated frames, sentence starts, triads, list shapes, and paragraph silhouettes
- restore writer-specific selection: the detail, stake, caveat, or judgement only this piece needs
- keep legitimate technical language, dialect, quotations, and intentional rhetoric

Use `references/genericity-and-stiffness.md` and `references/ai-isms-and-humanisation.md`. For a file-backed draft, the optional scanner can locate hotspots:

```bash
python3 scripts/scan_aiisms.py path/to/draft.md
```

**Pass when:** formulae no longer carry the argument, and the revision has more ownership and specificity without invented “human” decoration.

## Pass 7: Genre and delivery calibration

Now tune the finished piece to its destination.

- opening, headings, lists, and ending match the genre
- length serves the reader rather than a nominal target
- locale, terminology, and house style are consistent
- calls to action say what happens next
- code, commands, paths, citations, and links retain their exact form
- formatting makes the information easier to use

Use `references/genre-modes.md` and `references/style-bundles.md`.

**Pass when:** the piece feels native to its channel and still matches the preservation ledger.

## Pass 8: Final proof and stop

Read the opening, one middle section, and the ending aloud. Then run `references/quality-gates.md`.

Check the diff for accidental changes to:

- numbers, dates, names, quotations, links, commands, and identifiers
- uncertainty and source attribution
- paragraph meaning
- authorial voice anchors

Rerun any deterministic scanner after the last substantive rewrite.

**Pass when:** every applicable gate is satisfied and another edit would express preference rather than solve a named problem.

## Loopbacks

| Symptom | Return to |
|---|---|
| Clear sentences, wrong page | Pass 1 |
| Strong point, weak support | Pass 4 |
| Accurate prose, lifeless rhythm | Pass 5 |
| Smooth prose, generic voice | Pass 6 |
| “Human” rewrite lost precision | Pass 0 and Pass 4 |
| Genre pass reintroduced formulae | Pass 6, then final proof |
| Each edit makes the piece worse | Restore the last known-good version and read `references/gotchas.md` |

Do not restart the full stack after every small correction. Return only to the pass whose contract was broken, then run final proof again.
