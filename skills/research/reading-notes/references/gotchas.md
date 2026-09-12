# Gotchas

Use this reference when notes feel too thin, too confident, too noisy, or too hard to act on later.

## Partial Sources

Problem: the source is only a transcript, a screenshot, or rough notes.

Fix:

- Name the limitation in the Snapshot.
- Keep low-confidence inferences out of the main facts.
- Add missing context to Open Questions.
- Produce useful homework from what is available instead of blocking on completeness.

## Transcript Bias

Problem: video transcripts flatten demos, slide diagrams, code, pauses, and audience questions.

Fix:

- Use timestamps as anchors when available.
- Add a note when visual content may have been missed.
- If screenshots or slides are available, inspect them separately.
- Do not infer code details from spoken fragments unless the transcript is explicit.

## Shorthand Inflation

Problem: a small live-note fragment becomes an overconfident paragraph.

Fix:

- Preserve terse wording when meaning is uncertain.
- Use "possibly", "appears to", or Open Questions for ambiguous shorthand.
- Do not add background knowledge unless clearly separated as context or suggested research.

## Vague Homework

Problem: todos are broad nouns rather than actions.

Fix:

- Start each todo with a verb.
- Include the concrete object of the work.
- Add a success condition when useful.
- Split research, prototypes, writing tasks, and questions.

## Over-Summarization

Problem: the notes become a mini article and lose the user's future-work value.

Fix:

- Keep topic bullets short.
- Spend more detail on interesting ideas, research leads, and todos.
- Remove obvious filler such as "the speaker discussed".
- Keep only one level of nested bullets unless structure genuinely helps.

## Source Drift

Problem: the user asks for reading notes, but the assistant starts doing fresh research.

Fix:

- Summarize the provided source first.
- Put suggested lookups under Further Research.
- Only browse or verify live facts when the user asks, the source requires current status, or the host instructions require verification.

## Export Before Content

Problem: the assistant asks about file format before doing the thinking.

Fix:

- Produce notes in Markdown first.
- Ask the export question at the end.
- Skip the question only when the user already specified the desired format.
