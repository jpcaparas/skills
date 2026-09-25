---
name: eli12
description: "Explains codebases and feature flows in accessible language with grounded analogies. Use for simple walkthroughs or mental models; skip bug triage, code review, and code changes."
compatibility: "Works best in repositories where you can inspect files, search symbols, trace call paths, and optionally fan out read-only subagents for broad questions."
metadata:
  version: "1.0.0"
  repo_tags:
    - architecture
    - explanation
    - accessibility
    - teaching
references:
  - explainer-prompt
  - explorer-prompt
  - analogy-patterns
  - gotchas
---

# eli12

Explain code so a curious newcomer can build a correct mental model without drowning in jargon.

Inspired by [`poteto/how`](https://github.com/poteto/how), but tuned for accessibility: simpler language, tighter structure, and real-world analogies that stay anchored to the actual code.

## Decision Tree

1. If the user is asking how a subsystem, feature flow, runtime path, or file cluster works, use this skill.
2. Infer a bounded, useful scope from the conversation and repository context. Ask a short question only when unresolved ambiguity would materially change the explanation.
3. If the question is narrow and local to one function, class, hook, or file, explain directly from that code; use a focused search if its location or relevant connections are unknown.
4. For cross-module or end-to-end questions, delegate independent read-only exploration when it adds useful coverage and the harness supports it. Otherwise trace the flow directly; breadth alone does not require fan-out.
5. If the user mainly wants bugs, risks, or architectural critique, explain only enough to ground the discussion, then switch to normal review mode instead of staying inside the teaching frame.
6. If a real-world analogy would make the explanation fuzzier, use fewer analogies and stay closer to the code.

## Quick Reference

| Situation | Open / do | Why |
| --- | --- | --- |
| User asks something broad like "Explain this repo" with no target | Offer a bounded overview from context; clarify only material ambiguity | Prevents irrelevant architecture tours without blocking a useful answer |
| Need help with tone or explanation structure | Consult `references/explainer-prompt.md` | Keeps the answer direct and digestible |
| Need help tracing a broad subsystem or runtime flow | Consult `references/explorer-prompt.md` | Supports evidence gathering without a mandatory separate pass |
| Need better analogies without getting sloppy | Consult `references/analogy-patterns.md` | Maps abstract code ideas to grounded everyday systems |
| Unsure where simplification goes wrong | Consult `references/gotchas.md` | Avoids patronizing tone and misleading shortcuts |
| Need a ready-made output shape | Copy `templates/explanation-outline.md` | Gives a stable structure for the final explanation |
| Sanity-check prompt routing locally | Run `python3 scripts/probe_eli12.py --prompt "How does auth work?"` | Exercises advisory heuristics, not required questions, delegation, or reference reads |

## What This Skill Optimizes For

- building the smallest correct mental model first
- choosing a useful scope without an expensive repo tour
- defining jargon right when it appears
- using short, concrete paragraphs instead of wall-of-text explainers
- using friendly ASCII sketches when a flow or boundary is easier to see than to read
- tying every analogy back to real files, functions, and data flow
- helping the reader know where to look next in the codebase

## Default Operating Mode

1. Use the available context to choose a bounded explanation; ask only when materially different interpretations remain unresolved.
2. State your interpretation of the question once the target is clear.
3. Search for entry points, key types, and the files that actually move data or decisions.
4. Trace the real path from trigger to effect. Do not explain from filenames alone.
5. Collapse the findings into plain language.
6. Use grounded analogies if they help, then tie them back to exact code names. Direct explanation may be clearer.
7. Add a small ASCII sketch when topology, control flow, or data movement is easier to grasp visually than in prose.
8. Include a short map or next-read suggestion when it helps the reader verify or continue; inline file anchors may already suffice.

## Output Shape

Use the sections that help. Skip the ones that would add noise.

- **Big Picture** - What this thing does and why it exists.
- **Main Pieces** - The handful of concepts or files the reader needs in order to follow the rest.
- **The Story** - The step-by-step flow from input to output, trigger to effect, or request to response.
- **ASCII Sketch** - A compact text diagram for flow, boundaries, or ownership when that clarifies the system faster than prose.
- **Real-World Analogy** - A concrete analogy that matches the actual job of the system, not a cartoon version of it.
- **Where To Look** - The files and directories that matter most if the reader wants to verify or extend the explanation.
- **Sharp Edges** - Non-obvious behaviors, hidden state, historical quirks, or easy misunderstandings.

## Style Contract

### 1. Explain like a smart new teammate, not a child

Keep the language simple and digestible, but do not become cutesy, patronizing, or fake-cheerful.

### 2. Teach the system, not the syntax

Do not paraphrase every line of code. Focus on responsibilities, boundaries, data movement, and decision points.

### 3. Use analogies as scaffolding, not replacement

The analogy should help the reader get oriented. Immediately reconnect it to the real code so the explanation does not drift.

### 4. Define jargon on contact

If you must say "middleware," "idempotent," or "hydration," explain it in plain language the first time it appears.

### 5. Keep evidence visible

Name the actual files, symbols, or directories that support the explanation. Make it easy for the reader to verify the story.

### 6. Mark inference vs observation

If part of the explanation is inferred rather than directly observed, say so plainly.

### 7. Use ASCII sketches with discipline

Prefer a tiny chart over a paragraph only when it reduces confusion. Keep it narrow, label the real code concepts, and avoid decorative boxes.

Example:

```text
request
  -> auth middleware
  -> controller
  -> service
  -> database
```

### 8. Spend tokens on the right scope

For "How does this app work?", use context to select a useful overview or representative flow and state that boundary. Ask only if choosing among plausible targets would materially change the answer; do not substitute a whole-repo tour for a focused explanation.

## When To Fan Out

Fan out exploration only when independent work improves coverage and delegation is supported. These are possible opportunities, not automatic triggers:

- Broad architecture overviews
- Runtime flows that jump across layers
- Questions that span multiple packages or services
- Systems with separate data, orchestration, and UI concerns

Stay in one pass for narrow questions. Extra delegation slows simple explanations down.

## When Guidance Stops Helping

Repository behavior outranks a bundled analogy or workflow. When framework behavior is unclear, consult the installed version and relevant official documentation or trusted primary sources; state uncertainty if they are unavailable. If an example is stale or a rule makes explanations less useful, propose a canonical skill correction or deletion with the code/source evidence and a counterexample. Do not silently edit an installed copy.

## Reading Guide

These are optional targeted aids. Open only what resolves an explanation or exploration need; an ordinary answer does not require reference preloads.

| Need | Read |
| --- | --- |
| Core exploration workflow and evidence collection | `references/explorer-prompt.md` |
| Human-facing explanation tone and section shape | `references/explainer-prompt.md` |
| Everyday-system analogies that stay technically honest | `references/analogy-patterns.md` |
| Failure modes, oversimplification traps, and recovery | `references/gotchas.md` |
| High-level map of the reference set | `references/README.md` |

## Gotchas

1. Simpler language is not permission to hand-wave important behavior. If retries, caching, or background jobs matter, explain them plainly instead of omitting them.
2. A cute analogy that does not map to the real control flow is worse than no analogy at all.
3. Explaining a subsystem by listing files is not enough. Trace what actually happens.
4. If the user asked for one narrow thing, do not balloon the answer into a whole-architecture tour.
5. If the code is messy, say that directly. Accessibility should not sand off real complexity.
