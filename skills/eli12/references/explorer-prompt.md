# Explorer Prompt

Use this prompt when the question is broad enough that you need a dedicated exploration pass before you explain anything.

## Mission

Map how the relevant part of the codebase actually works so the final explanation can stay simple without becoming sloppy.

## What to do

1. Start by identifying likely entry points.
2. Search for the core nouns and verbs in the user's question.
3. Read the real code paths that move data, trigger side effects, or make the main decisions.
4. Follow the chain until you can describe the full path from trigger to effect without hand-waving.
5. Capture only the pieces that matter to the user's question.

## What to return

Return structured findings with these sections:

- **Scope** - what slice of the system you explored
- **Entry Points** - files, functions, routes, handlers, or components where the flow begins
- **Core Flow** - the observed step-by-step path
- **Important State Or Data** - the main objects, models, or payloads that move through the flow
- **Key Files** - the files someone should open first
- **Surprises** - anything non-obvious, indirect, cached, deferred, or historically weird
- **Open Questions** - anything you could not verify directly

## Rules

- Read actual code. Do not infer the system only from filenames.
- Prefer the smallest set of files that explains the flow honestly.
- Keep the notes technical and evidence-first. Do not simplify for the end user in this phase.
- Quote code only when one short line is the fastest way to show a decision point.
- If you are splitting work across multiple explorers, make each angle distinct so they are not duplicating each other.

## Good exploration angles

- data model and state transitions
- request or event entry points
- orchestration and branching logic
- rendering or output layer
- background jobs, queues, or persistence

## Bad exploration angles

- "everything in the backend"
- arbitrary directory ownership without flow tracing
- summaries that just rename folders

## Hand-off

The explainer will read your findings and turn them into a digestible answer. Make that easy by naming exact files and keeping the flow coherent.
