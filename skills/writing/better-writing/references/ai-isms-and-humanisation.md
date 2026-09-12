# AI-isms and humanisation

Use this reference to revise prose that feels generic, formulaic, machine-smooth, over-signposted, or unlike its writer.

The aim is better writing, not detector evasion. No word, punctuation mark, sentence shape, or model score can prove who wrote a passage. The editorial policy can still ban a canned rhetorical use from finished prose: the ban attaches to the phrase's function, not to every occurrence of its words.

## Contents

- [Start with three distinctions](#start-with-three-distinctions)
- [Editorial avoidance policy](#editorial-avoidance-policy)
- [Humanisation workflow](#humanisation-workflow)
- [Worked transformations](#worked-transformations)
- [Signal taxonomy](#signal-taxonomy)
- [Severity and confidence](#severity-and-confidence)
- [False-positive protections](#false-positive-protections)
- [Extending the corpus](#extending-the-corpus)
- [Humanisation gate](#humanisation-gate)

## Start with three distinctions

### Authorship is not style

A human can write formulaic prose. A model can produce an excellent sentence. AI-assisted wording also diffuses into ordinary human usage. Diagnose the page, not the person.

### A population signal is not a document verdict

Research can show that a word or structure became more common across millions of model-assisted texts. That does not make one occurrence suspicious in one draft.

### Humanisation is not camouflage

Do not add errors, slang, fragments, anecdotes, or punctuation variance to “look human.” Restore authorship through truthful selection, stance, detail, structure, and voice.

Read `references/research-notes.md` for the evidence and its limits.

## Editorial avoidance policy

Use three action levels:

| Action | Instruction |
|---|---|
| Remove | Delete assistant residue, empty ceremony, staged delivery, and other wrappers unless the destination genuinely needs them. |
| Rewrite | Rebuild a canned semantic frame from the source's actor, action, mechanism, evidence, comparison, or consequence. Do this even when the phrase occurs once. |
| Review | Inspect a contextual word, transition, punctuation habit, or structural pattern in density; retain precise and characteristic uses. |

Read `references/formulaic-language-catalogue.md` for the full phrase-family catalogue, natural rewrite moves, worked examples, and protected uses. Its central rule is firm: never satisfy an avoidance rule by swapping in a fashionable synonym.

The catalogue is much wider than a watch-word list. It covers reveal hooks such as `here's the kicker`, canned importance and benefit claims, vague appeals to research, academic boilerplate, scripted empathy, assistant residue, generic openings and endings, place-and-history glaze, sentimental narrative packaging, and dense lexical habits. `Gap` and `shift` simply illustrate the boundary: rewrite `bridge the gap` or `marks a significant shift` when they hide the proposition, but keep a measured pay gap, a defined research gap, a night shift, the Shift key, a phase shift, or distribution shift. The bare token is not the problem.

This policy applies to drafting as well as revision. Do not introduce a listed formula merely because it was absent from the source.

## Humanisation workflow

### 1. Protect the source

Record facts, numbers, quotations, citations, commands, identifiers, terminology, uncertainty, and voice anchors. Humanisation often fails by replacing precise source detail with lively invention.

### 2. Diagnose at several levels

Do not stop at vocabulary. Inspect:

- lexical choice
- sentence frames
- cadence and punctuation
- paragraph and section structure
- discourse and stance
- domain residue
- missing human signal

### 3. Apply the action level

Remove and rewrite rules do not need a cluster before they deserve an edit. Review-only signals usually do: several related cues in a short span matter more than one ordinary word or transition.

### 4. Rewrite from meaning

For each cluster, ask:

1. What claim is the sentence trying to make?
2. What evidence or experience supports it?
3. What relation is being staged: cause, contrast, sequence, example, or consequence?
4. What would the writer say without the frame?

Rewrite the sentence or paragraph. A thesaurus swap usually preserves the template.

### 5. Restore authorial signal

Add only what the source supports:

- a named actor, object, date, place, or interface
- a real mechanism or consequence
- a bounded judgement
- a specific uncertainty
- chronology that explains the result
- a detail from the writer's own experience
- a counterargument the writer genuinely considered

### 6. Read aloud and compare

Compare source and revision. Reject a change that lowers detector-like signals while making the prose less accurate, less accessible, less individual, or less natural.

### 7. Run the final diagnostic

For a substantial file-backed draft:

```bash
python3 scripts/scan_aiisms.py path/to/draft.md
python3 scripts/scan_aiisms.py --format json path/to/draft.md
python3 scripts/scan_aiisms.py --gate path/to/draft.md
```

The normal report includes single remove-, rewrite-, and review-labelled matches. `--gate` adds a nonzero exit only for explicit multi-pattern clusters within their configured scope. The scanner cannot evaluate genre or its own written exceptions, so it must not turn every lexical match into an automatic failure. Resolve or deliberately retain each candidate after contextual review. This is a revision aid, never an authorship gate.

## Worked transformations

Use these examples to learn the editorial move, not a replacement phrase. Each example assumes its stated details are present in the source. In real work, preserve the source's facts and leave unsupported specificity missing.

### Technical explanation: replace ceremony with mechanism

Before:

> In today's rapidly evolving infrastructure landscape, robust observability is more important than ever. It plays a critical role in empowering teams to navigate complexity with confidence.

After:

> The worker logs the job ID, attempt number, and provider response. When a batch stalls, on-call can see which request failed and whether retrying it would duplicate work.

The revision does not modernise the preamble. It answers what is observed and what decision that evidence supports.

### Analysis: unpack the compressed verdict

Before:

> The limitation is scope. This fundamentally changes how we should think about the result.

After:

> The study followed 24 volunteers from one office for two weeks. It can describe what happened in that group, but it cannot establish how customers in other regions would respond.

The shorter source sounded decisive while hiding the reason. The revision gives the boundary and consequence together.

### Reported prose: remove importance labels

Before:

> In a major development that underscores the growing urgency of the issue, the board has taken a significant step forward by approving the repairs.

After:

> The board approved $2.4 million for roof repairs on Thursday, three days after the library closed because rain reached the electrical room.

The event, amount, chronology, and consequence carry the weight. No adjective needs to assign importance in advance.

### Memo: replace a staged reveal with the decision

Before:

> This is not about slowing down. It is about ensuring that we move forward in the right way. The path ahead is clear: align, validate, and execute.

After:

> Delay the cutover until security validates the new vendor. The review is due Friday; if it passes, operations can keep the current Monday launch date.

The revision makes the actual decision, condition, and timing visible. The three-part slogan had hidden all three.

### Product copy: make the benefit cash out

Before:

> Our innovative platform empowers modern teams to collaborate seamlessly and unlock their full potential.

After:

> Reviewers comment, approve, and compare revisions in one queue, so the release owner no longer reconciles separate email threads.

This repair is valid only when the product really works that way. Without a supported mechanism, narrow or remove the claim.

### Email: remove the assistant wrapper

Before:

> I hope this message finds you well. I wanted to reach out regarding the revised budget and kindly ask whether you might be able to share your thoughts at your earliest convenience.

After:

> Could you approve the revised budget by Thursday? The contractor cannot start until we confirm the amount.

The courtesy remains in the direct request and useful context. The email no longer makes the reader excavate the ask.

### UI copy: name the state and recovery

Before:

> Something went wrong. Please try again to continue your journey.

After:

> We could not save the address. Check the postcode, then try again.

The revision replaces a generic failure and ornamental metaphor with the failed object and a plausible next action. Do not invent a recovery step the product does not support.

### Reflection: remove the explained moral

Before:

> That day taught me that resilience is not about avoiding difficulty; it is about embracing the journey and emerging stronger on the other side.

After:

> On Monday I put the cracked mug back beside the kettle. I still reached for it first on Tuesday.

The image can carry the turn without a universal lesson. Keep an explicit reflection when the writer genuinely thinks it; remove it when it only explains what the scene already showed.

### Missing evidence: delete or ask, do not improvise

Before:

> Trusted by leading organisations worldwide, the service delivers proven results at scale.

When the source contains no names, scale, or results, there is no responsible specific rewrite. Delete the claim or ask for the customer, measure, and comparison. Replacing `leading` with `forward-thinking` preserves the same evidence gap.

### Mechanical formatting: restore an argument

Before:

> **Speed:** Work moves faster.
>
> **Clarity:** Everyone stays aligned.
>
> **Impact:** Teams achieve better outcomes.

After, when the source supports the mechanism:

> The shared queue gives reviewers one current version and records each approval. Release owners spend less time reconciling comments and can see which decision is holding the work.

The revision removes a decorative three-part list because the ideas were not useful peers. If the source contains three genuinely comparable measures, a list or table may still be the clearest form.

For paragraph-level formulae, repeated section silhouettes, or wall-of-text repair, read `references/natural-structure-and-digestibility.md` and rebuild the order as well as the sentences.

## Signal taxonomy

### 1. Lexical over-representation

Some models overproduce prestige verbs, decorative adjectives, and abstract nouns. Common examples change over time and by model, domain, prompt, and training method.

Inspect:

- several fashionable words clustered together
- an ornate verb where a plain exact verb would do
- synonym clusters that repeat the same evaluative work
- adjectives that announce complexity, importance, or novelty without evidence
- abstract nouns outnumbering named actors and objects

Do not ban a useful spelling in every setting. `Landscape` can describe land; `robust` has precise statistical and engineering uses; `delve` may be the writer's natural verb. Ban vague rhetorical uses by default and protect exact ones. Function matters more than the token.

Repair: name the mechanism, object, comparison, or consequence.

### 2. Significance and authority frames

These frames tell the reader how much weight to assign before the sentence earns it:

- importance preambles
- declarations that a pattern, distinction, or limitation “matters”
- claims of fundamental difference without naming the practical difference
- vague authority such as unnamed experts or leading organisations
- compressed conclusions stated as universal maxims

Examples of compressed authority:

- `The pattern that keeps showing up ...`
- `The limitation is scope.`
- `Here's how I actually decide.`
- `That's a fundamentally different approach.`
- a bare claim that a policy, constraint, or preference “matters” without saying how

These frames are rewrite prompts when they compress evidence or consequence. A cluster raises the priority because several sentences arrive already packaged as verdicts.

Repair: unpack the evidence and consequence.

> Eligibility rules matter.

becomes, when supported:

> Applicants without a local address cannot use the online form, so they must apply at a service centre.

### 3. Reveal and contrast templates

Watch for repeated versions of:

- reject X, reveal Y
- `not X, not Y, just Z`
- `you do not need X; you need Y`
- a question fragment followed by a slogan answer
- before/after claims staged as a dramatic reversal

Contrast is useful. The problem is turning every distinction into a reveal.

Repair: lead with the supported claim; keep the comparison only if it adds information.

### 4. Teacher and presenter scaffolds

Signals include:

- canned analogies that begin by telling the reader how to imagine the concept
- invitations to dive in, unpack, explore, or break something down
- stage directions such as “here is the interesting part”
- slide-deck transitions and numbered scaffolds left over from an assistant answer
- explanations that over-teach a reader who already knows the domain

Repair: answer directly, then add an analogy only if it resolves a real confusion.

### 5. Service and chat residue

Look for:

- praise for the question
- cheerful permission or offers of more help
- assistant disclaimers
- generic greetings and closers
- unnecessary restatement of the request
- every answer forced into a list

Repair: remove the service wrapper and keep the useful content.

### 6. Corporate, marketing, and professional glaze

Common forms:

- benefits without mechanisms
- celebratory announcements without a concrete event
- strategic abstractions that could fit any company
- urgency built from a fictional group of winners and losers
- cover letters that praise the organisation but reveal no fit
- landing pages with proof-shaped language but no proof

Repair: name the work, audience, constraint, evidence, or result. Never invent a metric to replace an adjective.

### 7. Formatting residue

Inspect:

- every bullet beginning with a bold label and colon
- a heading for every short paragraph
- generic headings such as overview, key takeaways, and what comes next
- decorative arrows, emoji, or callouts that do not carry meaning
- lists used where an argument needs sentences
- a tidy three-item structure repeated section after section

Repair: choose formatting from the information shape. Keep accessible navigation and legitimate comparison structures.

### 8. Cadence and punctuation regularity

Potential clusters:

- sentence lengths with little meaningful variation
- several sentences beginning with the same shell
- repeated three-part cadence
- a run of punchy fragments
- paragraph lengths that form a mechanical silhouette
- question marks used mainly for suspense
- dashes, semicolons, colons, or parentheses used at a conspicuously steady rate

No punctuation mark is an AI tell by itself. An em dash can be exactly right. Revise when punctuation is performing sophistication or drama instead of syntax.

Repair: join or split where the thought asks; let punctuation express grammatical relationships.

### 9. Discourse and stance regularity

Inspect:

- each paragraph opening with a claim and closing with a summary of the same claim
- a conclusion that repeats the whole piece and restores generic optimism
- balanced pros and cons that avoid a supported verdict
- hedging spread across the sentence instead of attached to the uncertain claim
- counterarguments acknowledged ceremonially but not answered
- every section following identical claim, explanation, example, lesson order

Repair: vary structure because the reasoning varies. State the verdict the evidence permits; keep uncertainty local and explicit.

### 10. Semantic echo and over-explanation

Signals include:

- one useful point restated through several metaphors
- section summaries nested inside article summaries
- theme or moral explained after the image already carried it
- instructions that repeat the step without adding a reason or check
- conclusions longer than the evidence they conclude

Repair: keep the strongest statement, then add evidence or move on.

### 11. Missing human signal

A surface-clean draft may still feel anonymous because it lacks:

- ownership or a visible source of judgement
- time and place
- embodied or operational detail
- a real stake
- domain friction
- an opinion that costs something
- culturally or personally specific language
- irregular but meaningful chronology

Do not manufacture these. Ask the writer for missing experience or leave the claim properly impersonal.

### 12. Narrative flattening

In narrative and reflective work, inspect:

- tidy single-track chronology
- explicit moral explanations
- uniform emotional temperature
- generic character description
- conflict resolved into a lesson too cleanly
- the narrator knowing more than their position allows

Repair: preserve ambiguity, causal mess, temporal movement, and what the narrator did not know at the time.

## Severity and confidence

Keep these dimensions separate.

| Dimension | Question |
|---|---|
| Severity | How much does the pattern damage this passage? |
| Confidence | How likely is the match to represent the described writing problem? |
| Occurrence | Is it isolated or repeated? |
| Evidence tier | Is the pattern supported by research, corpus observation, or editorial experience? |
| Confound risk | Could genre, dialect, translation, accessibility, quotation, or technical usage explain it? |

Suggested interpretation:

- **Low:** optional editorial note; one weak signal never gates.
- **Medium:** inspect in context and revise if the passage improves.
- **High:** a repeated, high-confidence frame or cluster that is actively obscuring meaning.

Even a high signal is not an authorship verdict.

Action is separate from both dimensions:

- **Remove** means the frame has no useful job in the finished artefact unless a named genre exception applies.
- **Rewrite** means the underlying thought may matter, but the formula cannot carry it.
- **Review** means context, density, and writer preference decide.

A low-severity phrase can still be remove-by-default because deletion is harmless. A high-severity signal can remain review-only when the scanner cannot distinguish a technical use safely.

## False-positive protections

Before changing a match, check whether it is:

- inside code, a command, URL, citation, quotation, title, or blockquote
- an identifier, UI label, official name, or required term
- literal rather than rhetorical
- measured, defined, or established technical language
- established in the writer's samples
- normal for the genre or accessibility level
- part of a deliberate parallel structure
- written by a second-language author whose voice would be erased by “correction”
- the most precise wording available

If so, retain it or revise around it without corrupting the source.

## Extending the corpus

The machine-readable catalogue lives at `assets/aiisms.json`. Add a pattern only when it passes these gates:

1. **Recurrence:** it appears independently, not as a single disliked line.
2. **Generality:** it represents a reusable writing failure rather than one topic or writer.
3. **Testability:** positive examples and counterexamples can distinguish the pattern.
4. **Repairability:** the entry names the buried meaning and a reconstruction move, not a synonym.
5. **Calibration:** severity, confidence, minimum occurrence, exceptions, evidence, and review date are explicit.
6. **Safety:** it does not turn dialect, disability, second-language writing, or ordinary punctuation into suspicion.

Update the corpus, tests, and explanatory reference together. Retire patterns whose meaning, evidence, or false-positive rate no longer justifies them.

## Humanisation gate

A revision passes when:

- it is more accurate or clear, not merely less formulaic
- remove-by-default wrappers are gone unless the genre requires them
- rewrite-by-default frames no longer carry the claim
- high-confidence clusters have been resolved or deliberately retained
- no fact, literal, qualification, citation, or voice anchor was lost
- no fake experience or stylistic mess was added
- dialect, accessibility, and author identity remain respected
- the prose contains the detail, stance, and structure this particular reader needs
