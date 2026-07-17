# Natural structure and digestibility

Use this reference when prose has the wrong order, buries its point, overloads paragraphs, reads as a wall of text, or has been chopped into notes in the name of clarity.

The aim is not uniformly short writing. It is a visible path through the material: the reader knows why each part is present, how it connects to the last part, and what to carry forward.

All worked examples below are invented. Their facts belong only to the example and are not reusable evidence.

## Contents

- [Learn from publications without copying them](#learn-from-publications-without-copying-them)
- [Build around the reader's next question](#build-around-the-readers-next-question)
- [Restructure in six moves](#restructure-in-six-moves)
- [Worked structural recasts](#worked-structural-recasts)
- [Break long prose at changes of job](#break-long-prose-at-changes-of-job)
- [Choose the form from the information](#choose-the-form-from-the-information)
- [Worked digestibility repairs](#worked-digestibility-repairs)
- [Know when not to split](#know-when-not-to-split)
- [Structure and digestibility gate](#structure-and-digestibility-gate)

## Learn from publications without copying them

Strong mainstream editing offers transferable habits rather than one universal house voice:

- select the main development, decision, question, or pressure before drafting the opening
- rank information instead of giving every fact equal weight
- place explanation and attribution beside the claim they support
- ask what the reader needs to know next
- vary paragraph and sentence scale with the material
- rewrite borrowed structure and language from the underlying facts
- end by doing the genre's closing job, not by recapping on autopilot

These habits travel well. Newsroom forms do not always travel with them. An inverted pyramid suits a breaking update but can flatten an essay, proposal, tutorial, or reflective piece. Neutral attribution is vital in factual reporting but does not require a personal essay or recommendation memo to hide its position. Read `references/research-notes.md` for the publication sources and their limits.

## Build around the reader's next question

Natural structure feels inevitable because each part creates or answers a real question.

| After the reader learns... | A likely next need is... |
|---|---|
| what happened | how, why, who is affected, and what remains unknown |
| the recommendation | the evidence, trade-off, owner, and next decision |
| the task | the starting state, steps, verification, and recovery |
| the claim | the mechanism, example, qualification, and implication |
| the scene | the pressure inside it, what changed, and what the narrator now sees differently |
| the offer | who it is for, how it works, proof, objections, and the next action |

Do not answer every possible question. Answer the questions required by this reader and genre, in the order that makes the material easiest to understand or use.

## Restructure in six moves

### 1. State the destination

Write one private sentence that names what the reader should understand, decide, feel, or do by the end. If two unrelated outcomes appear, the piece may need separate sections or separate artefacts.

### 2. Reverse-outline the source

Label each paragraph or sentence by its job, not its topic:

```text
context
decision
evidence
same evidence again
limitation
action
```

The labels reveal buried points, duplicate work, and missing bridges without committing to new wording.

Keep these labels in the working outline. Do not automatically publish `Finding`, `Evidence`, `Limit`, or `Recommendation` as headings. Add headings only when the finished piece is long enough to need navigation or readers will revisit sections independently.

### 3. Rank the moves

Put the genre's central move where readers expect it. A memo usually needs the decision early; an instruction needs the task and starting state; a reported update needs the development; an essay may earn a delayed thesis through scene or tension.

### 4. Group by governing job

Keep a claim with the evidence or explanation that lets the reader assess it. Split when the paragraph changes job, not when it crosses a preferred length. Merge adjacent fragments when they are really one thought.

### 5. Restore the links

Name cause, contrast, sequence, example, or consequence where the relation is not obvious. A clean paragraph break does not remove the need for connective tissue.

### 6. Choose the display and reread

Use prose, headings, lists, or a table according to the information shape. Then read only the first sentence of each paragraph. Those sentences should form a useful skeleton without turning every paragraph into a miniature summary.

## Worked structural recasts

### Decision memo: put the call before the chronology

Before:

> Over the past several weeks, the operations group has continued to evaluate the proposed supplier change as part of our broader efficiency programme. Several stakeholders have contributed useful perspectives, and a number of considerations have emerged. The new supplier quoted 8% less, but it has not completed the security review, so after careful consideration we believe it may be prudent to delay signing until Friday.

After:

> Delay the supplier agreement until Friday, when the security review is due.
>
> The new supplier quoted 8% less than the current provider. That saving is not yet enough to justify signing: security has not approved the change, and the source does not establish what remediation might cost if the review finds a problem.

The revision preserves the price difference and the cautious recommendation. It removes process theatre, gives the recommendation a reason, and keeps the evidence gap visible.

### Analysis: answer before touring the topic

Before:

> Caching is an increasingly important consideration in modern distributed systems. There are many different approaches, each with benefits and challenges. It is therefore essential to understand the key distinction between cache invalidation and cache expiry. In the following section, we will explore what this means in practice.

After:

> Expiry removes a cached value after a set time. Invalidation removes it when the underlying data changes. The choice affects how long a reader may see stale data: expiry accepts a bounded delay, while invalidation depends on every relevant change producing a reliable signal.

The revision does not find fresher synonyms for the ceremony. It replaces the ceremony with the mechanism and consequence.

### Reported update: lead with the event, then source and consequence

Before:

> In a significant development that has prompted concern across the community, local officials have taken decisive action following a range of issues that came to light during a recent process of inspection at the Riverside footbridge.

After:

> The council closed the Riverside footbridge on Tuesday after an inspection found a cracked support plate. The closure notice gives no reopening date; pedestrians are being diverted 600 metres to the Mill Street crossing.

The opening now supplies the event, source boundary, and practical consequence. It does not tell readers that the development is significant; the closure and detour show why it matters.

### Technical guide: let the reader start the task

Before:

> Modern development environments involve a wide range of moving parts, and effective verification plays a crucial role in ensuring a seamless experience. Before diving into the steps below, it is important to understand that health endpoints can provide useful information about service availability.

After:

> Start the worker with the local profile, then check `http://localhost:8787/healthz`. Treat a healthy response as evidence that the endpoint answered. It does not by itself prove that the worker is processing jobs or that queued jobs can reach their dependencies.

The revision gives the action first and keeps the limitation beside the verification claim.

### Reflection: let the scene create the thought

Before:

> Change is difficult, but it also teaches us valuable lessons about resilience. I learned this one rainy morning when the first bus passed without stopping, and the second never arrived.

After:

> The first bus passed with its lights off. By the time the timetable admitted the second one was not coming, rain had soaked the paper bag around my lunch.
>
> I had spent the week telling my team that the delayed launch was still under control. At the bus stop, with no useful update to give myself, that sentence sounded different.

The revision does not announce the lesson. It lets a specific scene put pressure on an earlier claim and leaves room for the reader to make the connection.

## Break long prose at changes of job

A paragraph is a unit of thought, not a container with a word limit. Consider a break when the prose moves:

- from claim to a substantial body of evidence
- from evidence to a limitation or counterexample
- from diagnosis to recommendation
- from one step, actor, time, place, or source to another
- from general rule to a worked example
- from present action to background that readers may skip
- from one reader task to another, such as understanding to deciding

Keep the paragraph together when the sentences perform one tightly connected movement and a split would separate:

- a claim from the short reason that makes it credible
- a condition from its consequence or exception
- steps in a causal chain the reader must hold together
- a quotation from essential attribution or explanation
- an image from the turn it creates in a narrative

Paragraph length is evidence to inspect, not a verdict. A two-sentence paragraph can be overloaded; a six-sentence paragraph can be lucid.

## Choose the form from the information

| Information shape | Usually use | Do not use it merely to... |
|---|---|---|
| developing claim or causal explanation | paragraphs | avoid writing transitions |
| ordered actions | numbered list with one top-level item per meaningful checkpoint | make unordered advice look procedural or give every verb its own step |
| genuine peers, options, checks, or evidence | bullets | decorate every paragraph with a label |
| repeated fields across several items | table | compress nuanced argument into cells |
| long piece with distinct reader destinations | informative headings | label generic furniture such as `Overview` |
| exceptional risk or irreversible consequence | warning or callout | make ordinary information look urgent |

Lists improve comparison and retrieval. Paragraphs carry development, qualification, and voice. A digestibility pass often needs both, but each should keep the work it does best.

A command does not automatically deserve its own top-level step. Group small actions when they lead to the same checkpoint and can be understood safely together. Start a new step when the reader must verify a result, choose a branch, change tools or context, or recover from failure.

Phrase an unperformed verification as an instruction and an expected result: `Run X; expect Y`. Reserve declarative wording such as `Y is confirmed` for a result that was actually observed. A structural rewrite must not turn a planned check into evidence of success.

## Worked digestibility repairs

### Dense analysis: separate finding, limit, and action

Before:

> In the June pilot, 37 of 40 imports finished within 12 minutes while three remained in `processing` until support restarted the worker, and although the logs show that all three stalled after the provider returned a 429 response, the team has not reproduced the stall and cannot yet tell whether the worker ignored the retry delay or the provider failed to send one, which means the proposed 10% rollout may reduce the overnight backlog but could also leave support with more manual recovery, so product recommends enabling the queue for one internal account while engineering adds the response headers to the log and support records every restart.

After:

> In the June pilot, 37 of 40 imports finished within 12 minutes. Three remained in `processing` until support restarted the worker; each had stalled after the provider returned a 429 response.
>
> The team has not reproduced the stall. The current logs do not show whether the worker ignored a retry delay or the provider failed to send one, so the effect of a wider rollout remains uncertain.
>
> Product recommends enabling the queue for one internal account, not 10% of customers. During that run, engineering would add the response headers to the log and support would record every restart.

The breaks mark changes of job: finding, limit, then recommendation. The semicolon in the first paragraph keeps the stalled imports and their shared evidence together. The revision also makes the proposed scope unambiguous instead of burying it in one causal chain.

### Dense procedure: expose the sequence and the stop condition

Before:

> Export the current rules with `rules export --out rules.json`, open the file and confirm that `schema_version` is `3`, then run `rules migrate rules.json --check`; if the check reports an unknown action, stop and update the mapping file, otherwise run `rules migrate rules.json --write` and finally use `rules diff --against rules.json` to confirm that only action names changed.

After:

> Export and inspect the current rules:
>
> 1. Run `rules export --out rules.json`.
> 2. Open `rules.json` and confirm that `schema_version` is `3`.
> 3. Run `rules migrate rules.json --check`.
>
> If the check reports an unknown action, stop and update the mapping file, then run `rules migrate rules.json --check` again. Do not run `rules migrate rules.json --write` until the check no longer reports an unknown action.
>
> Finish with `rules diff --against rules.json`. Confirm that the diff contains only action-name changes.

The numbered list earns its place because the actions are ordered. Its top-level items mark meaningful checkpoints rather than every small verb. The failure branch returns to prose so it cannot be mistaken for another routine step, its recovery loop is explicit, and verification gets its own closing job without implying success.

### Over-chunked prose: reconnect the reason

Before:

> The pilot was small.
>
> It included eight people.
>
> They were all existing customers.
>
> We should not treat the result as a launch forecast.

After:

> The pilot included eight existing customers, so its results should not be treated as a launch forecast.

White space had hidden one qualification across four dramatic fragments. Joining the sentences restores the evidential relationship.

## Know when not to split

Keep continuous prose when the reader benefits from holding the whole relation in view.

> Retry the request only if the provider returned `429`, supplied a positive `retry_after_ms`, and did not acknowledge the original idempotency key; if any one of those conditions is unknown, move the job to manual review.

This sentence is dense because the policy is conjunctive. Turning each condition into a separate paragraph would obscure that all three must be true. A bullet list could help in a reference page, but the final consequence still needs to remain visibly attached to the full condition.

Narrative can also earn a longer paragraph through accumulation, and legal or regulated prose may need clauses to stay together for scope. Improve the syntax first. Split only when the meaning survives the break.

## Structure and digestibility gate

The revision passes when:

- the opening performs the right job for the genre
- the order follows the reader's likely questions or required actions
- each paragraph has one governing job without becoming a slogan fragment
- claim, evidence, attribution, qualification, and consequence remain correctly attached
- headings, lists, and tables reflect real information shapes
- numbered steps represent meaningful actions or checkpoints rather than mechanically atomising every command
- transitions name necessary logic without presenter scaffolding
- long sentences or paragraphs remain only when their parts belong together
- the ending decides, verifies, asks, acts, or turns outward as the genre requires
- no fact, uncertainty, literal, source boundary, or voice anchor was lost during restructuring

## See also

- `references/genre-modes.md` for the destination shape of the finished artefact
- `references/revision-pass-stack.md` for the order of structural and sentence passes
- `references/voice-and-rhythm.md` for reconnecting clipped prose and varying cadence
- `references/ai-isms-and-humanisation.md` for paragraph-level formulae and machine-smooth structure
- `references/quality-gates.md` for final fidelity and delivery checks
