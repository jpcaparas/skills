# to-diagram

General-purpose Agent Skill for turning a convoluted engineering, scientific, or everyday process into one clear Mermaid diagram and two matching deliverables: Markdown source and an exported PNG.

## Install

```bash
npx skills add jpcaparas/skills --skill to-diagram
```

## Invoke

```text
/to-diagram <process, concept, source path, or pasted notes>
```

The skill selects the simplest fitting Mermaid grammar, compresses detail without hiding material branches or uncertainty, renders the PNG through Mermaid CLI, and verifies both meaning and visual readability.

## Runtime requirements

- Python 3.11 or newer
- Mermaid CLI v11 on `PATH`, or Node.js with `npx`
- Optional non-standard Mermaid CLI path through `--mmdc` or `TO_DIAGRAM_MMDC`

`SKILL.md` is the authoritative behavior contract. The renderer, evals, and local checks validate the two-file output and invocation boundaries.
