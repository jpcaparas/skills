# eli12

Installable skill for explaining codebases in clear, digestible language without flattening the technical truth.

`eli12` is inspired by [poteto/how](https://github.com/poteto/how), but it shifts the voice from senior-engineer onboarding to accessible teaching. The goal is not a literal "explain like I'm 12" gimmick. The goal is a simpler, more human explanation style that uses grounded analogies and keeps the reader oriented.

## What it covers

- narrow code walkthroughs for specific files, classes, hooks, or helpers
- broader subsystem explanations with exploration-first synthesis
- end-to-end feature and runtime flow explanations
- analogy-driven teaching that stays tied to actual code symbols and paths
- structured explanations with file maps and sharp-edge callouts

## Key files

- `SKILL.md` - authoritative routing and explanation contract
- `references/explorer-prompt.md` - evidence-gathering workflow for broad questions
- `references/explainer-prompt.md` - accessible explanation style and output shape
- `references/analogy-patterns.md` - analogy rules and reusable concept mappings
- `scripts/probe_eli12.py` - local routing probe for trigger and complexity checks
