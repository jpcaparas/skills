---
name: eli12
description: "Explains how a codebase, subsystem or feature flow works in plain language with grounded analogies. Use for 'explain this simply', walkthroughs and mental models. Not for bug triage, code review or code changes."
---

# eli12

Give a curious new teammate a correct mental model of how the code works, in plain language, anchored to real files and symbols. Inspired by [`poteto/how`](https://github.com/poteto/how), tuned for accessibility.

## Scope

Infer a bounded scope from the conversation and repository. A broad "explain this repo" can be answered with a stated overview or one representative flow; ask one short question only when materially different targets remain, as with two unrelated subsystems. A question about one function or file is answered directly from that code. If the user mainly wants bugs, risks or critique, explain only enough to ground it, then switch to normal review.

Trace the real path from trigger to effect before explaining; never explain from filenames. Fan out read-only exploration only for questions that span several packages or layers and when independent angles add coverage; otherwise trace it yourself.

## Writing it

- Smart new teammate, not a child: plain, concrete, no cutesy tone. Short paragraphs, few bullets.
- Open with the big picture, then the few concepts that matter, then the story from input to output. Teach responsibilities, boundaries and decision points, not line-by-line syntax.
- Define jargon (middleware, idempotent, hydration) where it first appears.
- Name the actual files and symbols so the reader can verify. Say which statements are inferred rather than observed.
- Use an analogy only when it matches the real job of the code and can be tied back to exact symbols at once ("the retry queue is a call-back list at a repair shop: the worker re-enqueues failed tasks with a delay"). Skip analogies for exact algorithms, security constraints and concurrency, where they hide races or limits. If the analogy mismatches the code somewhere that matters, name the mismatch.
- A tiny ASCII sketch (`request -> auth -> controller -> service -> db`) when flow or ownership is faster to see than to read.
- End with where to look next when it helps.

Pick only the sections that help from: Big Picture, Main Pieces, The Story, Sketch, Analogy, Where To Look, Sharp Edges.

## Gotchas

- Simple is not hand-waving: if retries, caching, feature flags, tenant state or background jobs change the behaviour, say so plainly.
- Listing folders is not an explanation; trace what happens.
- Answer the asked flow first instead of ballooning into an architecture tour.
- If the code is tangled, say so and point to the confusing seams.
- Repository behaviour outranks any analogy; when framework behaviour is unclear, check the installed version or official docs and flag the uncertainty.
