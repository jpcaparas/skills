---
name: to-diagram
description: "Creates Mermaid diagrams (flowchart, sequence, state, cycle) of engineering, scientific or general processes, exported as Markdown plus PNG. Use for /to-diagram or requests to diagram a process. Not for data charts or infographics."
compatibility: "Python 3.11+ and either Mermaid CLI v11 (`mmdc`) on PATH or Node.js with npx."
---

# To Diagram

Invocation: `/to-diagram <process, concept, source path, or pasted notes>`, optionally with an output basename or directory.

Deliver exactly two files from one Mermaid source of truth: `<slug>.md` (explanation plus one fenced `mermaid` block) and `<slug>.png` (render of that same block). No `.mmd`, `.svg` or other sidecars. The slug is a short kebab-case name for the subject, written to the current directory unless told otherwise; if either file exists, take the next free numeric suffix (`order-flow-2`) rather than overwrite.

## Content

- Read every source the user supplied before drawing; for code, follow entrypoints, transitions, side effects, retries and terminal outcomes. Every node and edge must be supported by the source, marked as an inference, or listed as an assumption. Ask one question only when two readings would give materially different diagrams.
- One diagram, one grammar, chosen by the reader's main question: `flowchart` for what happens, branches, loops or fails (`TD`, or `LR` for a short pipeline); `sequenceDiagram` for who exchanges what in what order; `stateDiagram-v2` for how one thing changes state; a flowchart with labelled feedback edges for cycles and mechanisms. Other grammars are allowed if the installed CLI supports them and they pass the same render check.
- Compress without distorting: group into named phases only when that clarifies; keep nodes needed for material branches, states and handoffs; label every decision outcome; show loops and failure paths only when they change understanding. Put examples, edge-case inventories and implementation detail below the diagram as prose.
- Engineering: keep trust boundaries, async handoffs, retry destinations and terminal failures. Science: never turn correlation into causation; label hypothesised or uncertain links. General audiences: replace jargon.
- Mermaid text is plain: simple node IDs, quoted labels, no HTML, scripts, click handlers, remote images or links. Meaning must not depend on colour alone.
- The Markdown states, briefly, the assumptions, inferences and omissions that could change interpretation.

## Rendering

```bash
python3 <skill-dir>/scripts/render_diagram.py "<slug>.md" "<slug>.png"
```

The renderer extracts the single Mermaid block, runs Mermaid CLI (neutral theme, white background, 2× scale), validates the PNG, and cleans up its temp files. It prefers `mmdc` on PATH, else `@mermaid-js/mermaid-cli@^11` via npx; use `--mmdc /path` or `TO_DIAGRAM_MMDC` for another install. Do not pass `--force` unless the user authorised replacing that PNG.

If rendering fails, fix the Mermaid and rerun. Never substitute a screenshot or an image generator, and never report done with only the Markdown. If the tool or version guidance conflicts with the installed CLI, check `--version`/`--help` and official Mermaid docs, and propose a sourced fix to this skill rather than editing an installed copy.

## Before handing off

Look at the PNG (when you can view images) for clipping, density, contrast and arrow readability, and trace every branch to a terminal outcome or intentional loop against the source. Simplify and re-render if the main path is not obvious. If you cannot view images, say so. Then give the user the two paths and any assumptions that could change interpretation.
