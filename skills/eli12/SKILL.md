---
name: eli12
description: "Surgically explain how a codebase, subsystem, feature flow, or cluster of files works in clear, accessible language. Use when the user asks 'how does this work?', wants a code walkthrough, needs architecture explained simply, or wants a digestible mental model with grounded real-world analogies. Trigger on: 'explain this codebase', 'walk me through the flow', 'how does X work', 'what happens when', 'eli12', 'explain it simply', 'make this architecture easier to understand'. Do NOT use for bug triage, code review, literal children's storytelling, or requests that primarily need code changes instead of explanation."
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
2. If the question is narrow and local to one function, class, hook, or file, do a direct explain pass after a focused code search.
3. If the question spans multiple modules, services, or an end-to-end flow, split it into 2-4 exploration angles, gather findings in parallel when the harness allows it, then synthesize.
4. If the user mainly wants bugs, risks, or architectural critique, explain only enough to ground the discussion, then switch to normal review mode instead of staying inside the teaching frame.
5. If a real-world analogy would make the explanation fuzzier, use fewer analogies and stay closer to the code.

## Quick Reference

| Situation | Open / do | Why |
| --- | --- | --- |
| Explain one file, class, or helper simply | Read `references/explainer-prompt.md` | Keeps the answer direct and digestible |
| Explain a broad subsystem or runtime flow | Read `references/explorer-prompt.md`, then `references/explainer-prompt.md` | Gather evidence first, simplify second |
| Need better analogies without getting sloppy | Read `references/analogy-patterns.md` | Maps abstract code ideas to grounded everyday systems |
| Unsure where simplification goes wrong | Read `references/gotchas.md` | Avoids patronizing tone and misleading shortcuts |
| Need a ready-made output shape | Copy `templates/explanation-outline.md` | Gives a stable structure for the final explanation |
| Sanity-check prompt routing locally | Run `python3 scripts/probe_eli12.py --prompt "How does auth work?"` | Verifies trigger and complexity heuristics |

## What This Skill Optimizes For

- building the smallest correct mental model first
- defining jargon right when it appears
- using short, concrete paragraphs instead of wall-of-text explainers
- tying every analogy back to real files, functions, and data flow
- helping the reader know where to look next in the codebase

## Default Operating Mode

1. State your interpretation of the question if the scope is fuzzy.
2. Search for entry points, key types, and the files that actually move data or decisions.
3. Trace the real path from trigger to effect. Do not explain from filenames alone.
4. Collapse the findings into plain language.
5. Use one grounded analogy per important concept, then tie it back to exact code names.
6. End with a short map of where the important pieces live.

## Output Shape

Use the sections that help. Skip the ones that would add noise.

- **Big Picture** - What this thing does and why it exists.
- **Main Pieces** - The handful of concepts or files the reader needs in order to follow the rest.
- **The Story** - The step-by-step flow from input to output, trigger to effect, or request to response.
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

## When To Fan Out

Fan out exploration only when it improves coverage.

- Broad architecture overviews
- Runtime flows that jump across layers
- Questions that span multiple packages or services
- Systems with separate data, orchestration, and UI concerns

Stay in one pass for narrow questions. Extra delegation slows simple explanations down.

## Reading Guide

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
