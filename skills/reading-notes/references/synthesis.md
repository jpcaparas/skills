# Synthesis Method

Use this reference to turn extracted source material into topics, interesting ideas, research leads, and homework todos.

## Topic Map

Create the topic map before the final notes.

Good topic bullets:

- name the subject plainly
- explain why it appears in the source
- group related fragments that appeared in different places
- preserve key vocabulary from the source

Weak topic bullets:

- copy full paragraphs from the source
- mirror every heading even when headings are noisy
- flatten everything into "miscellaneous"
- hide uncertainty

## Interesting Ideas

Promote an item to "interesting ideas" when it is one or more of these:

- surprising: it challenges a default assumption
- useful: it changes how the user might work
- transferable: it applies beyond the original resource
- controversial: it exposes a tradeoff or open debate
- concrete: it names a tool, command, architecture, pattern, RFC, paper, or example
- connected: it relates to something the user already appears to care about

Each idea should include a short "why it matters" clause. Do not list mere mentions.

## Homework Todos

Todos should be verb-first and doable later without reopening the source.

Prefer:

- "Read the PHP bound erased generic types RFC and note the proposed syntax and runtime erasure tradeoffs."
- "Prototype `Model::shouldBeStrict` in a fresh Laravel app and document which failures surface first."
- "Compare ClickHouse MergeTree and AggregatingMergeTree for dashboard aggregation workloads."

Avoid:

- "Research generics"
- "Look into testing"
- "Learn ClickHouse"

## Todo Fields

Use checkboxes by default. Add optional tags only when they clarify action.

```markdown
- [ ] [research] Read the PHP generics RFC and summarize the current proposal status.
- [ ] [prototype] Try `DB::prohibitDestructiveCommands()` in a local Laravel app and confirm behavior with forced destructive commands.
- [ ] [write] Draft a strict Laravel engineering checklist from the talk notes.
```

Useful tags:

- `[research]` for reading, watching, or fact-finding
- `[prototype]` for hands-on experiments
- `[verify]` for checking a claim, version, behavior, or current status
- `[write]` for turning notes into docs, posts, specs, or skills
- `[ask]` for questions to send to a speaker, teammate, or community
- `[decide]` for follow-up choices that need criteria

## Further Research

Research leads are not todos yet. They are search handles the user may want later:

- RFCs, standards, papers, books, talks, docs, repos, packages, people, products, commands, errors, concepts, datasets, and companies
- exact names and URLs from the source
- unclear terms that need verification

Keep these separate from todos so the action list does not become a glossary.

## Open Questions

Open questions capture uncertainty:

- missing context from a partial source
- a claim that needs current verification
- an ambiguous shorthand note
- a contradiction across sections
- something the user probably needs to ask a person

Phrase questions concretely:

- "Does `DB::prohibitDestructiveCommands()` block commands even when `--force` is provided in the target Laravel version?"
- "Which Nightwatch queries determine the ClickHouse primary key ordering?"

## Synthesis Pass

Use this sequence for most resources:

1. List raw anchors: headings, timestamps, URLs, named tools, commands, and claims.
2. Group anchors into 3-8 topics.
3. Select interesting ideas from the grouped material.
4. Convert high-value follow-up into todos.
5. Move passive terms into further research.
6. Move unsupported or ambiguous claims into open questions.
7. Tighten the output so every bullet has a job.

## Confidence Labels

Use light confidence labels when source quality varies:

- `High`: directly supported by the provided source.
- `Medium`: supported but compressed, paraphrased, or missing context.
- `Low`: inferred from shorthand, metadata, partial transcript, or incomplete access.

Do not overuse labels. A single confidence line in the Snapshot is usually enough.
