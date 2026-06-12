---
name: reading-notes
description: "Turn supplied resources into practical reading notes: topics, interesting ideas, research leads, open questions, and homework todos. Use for articles, PDFs, docs, webpages, videos, transcripts, slides, meetings, books, RFCs, or talks. Do NOT use for code review or exhaustive transcripts."
compatibility: "Requires resource access through the active harness. Optional: python3 for scripts/probe_reading_notes.py, scripts/validate.py, and scripts/test_skill.py."
metadata:
  version: "1.0.0"
  short-description: "Convert resources into topics, ideas, research leads, and homework todos"
  openclaw:
    category: "productivity"
    subcategory: "research"
    requires:
      bins: [python3]
    tags: ["notes", "research", "summarization", "todos", "study"]
references:
  - intake
  - synthesis
  - output-formats
  - gotchas
---

# Reading Notes

Turn supplied resources into useful review notes and a concrete homework list.

## Decision Tree

What did the user provide?

- Raw notes, pasted bullets, or a live note dump
  Treat the text as source material. Preserve the user's rough structure, repair obvious grouping, and extract homework without pretending the notes are complete.

- A local document, PDF, slide deck, spreadsheet, image, audio file, or video file
  Read `references/intake.md`, extract the available text and visual/audio signals, then continue with the default workflow.

- A webpage, article, RFC, issue, pull request, or public URL
  Read `references/intake.md`. Capture the title, URL, date if visible, and access limitations before summarizing.

- A YouTube or other video URL
  Read `references/intake.md`. Prefer a transcript or captions first, then supplement with visible metadata. If no transcript is available, say that and ask for one only after producing whatever can be grounded.

- The user asks for "homework", "stuff to research", "what should I do next", or "turn this into todos"
  Read `references/synthesis.md` and make the action list explicit.

- The user asks to save, export, share, or convert the notes
  Read `references/output-formats.md`. Produce the notes first, then ask which format to save unless the user already specified one.

## Quick Reference

| Need | Do |
| --- | --- |
| Classify a source quickly | `python3 scripts/probe_reading_notes.py --source "<resource-or-notes>"` |
| Extract from documents, videos, webpages, or screenshots | Read `references/intake.md` |
| Turn messy material into topics, ideas, todos, and research leads | Read `references/synthesis.md` |
| Use a stable Markdown structure | Copy `templates/reading-notes.md` |
| Save as Markdown, DOCX, PDF, or another format | Read `references/output-formats.md` |
| Avoid common summarization failures | Read `references/gotchas.md` |
| Validate the skill package | `python3 scripts/validate.py skills/reading-notes` |
| Run packaging and helper tests | `python3 scripts/test_skill.py skills/reading-notes` |

## Default Workflow

1. Identify the resource type and access path. If no resource is present, ask for the notes, link, file, transcript, or screenshot.
2. Capture source metadata: title, author/speaker if known, event/context, URL/path, date, and access limitations.
3. Extract content with the least lossy available method. For long resources, chunk by section, timestamp, heading, slide, or topic.
4. Build a topic map before writing final notes. Group by subject, not by the order in which fragments appeared.
5. Pull out interesting ideas: surprising claims, useful techniques, tradeoffs, open debates, references, named tools, and concepts worth revisiting.
6. Convert worthwhile follow-up into homework todos with concrete verbs: read, verify, compare, prototype, ask, install, benchmark, write, create, or decide.
7. Separate fact, inference, and question. Mark uncertain items instead of smoothing them into confident statements.
8. Return the notes in Markdown unless the user requested another format.
9. End by asking whether to save or export the notes, naming practical options such as Markdown, DOCX, PDF, or a task-list format.

## Output Contract

Use this shape by default. Omit empty sections, but keep the todo and research sections when the user wants homework.

```markdown
# <Resource or Session Title>

## Snapshot
- Context:
- Source:
- Confidence:

## Topics
- <topic>: <one-line explanation>

## Interesting Ideas
- <idea>: why it matters or why it is worth revisiting

## Homework / Todos
- [ ] <verb-first action>

## Further Research
- <term, tool, paper, RFC, person, library, or question to look up>

## Open Questions
- <uncertainty, missing source, or question to ask later>
```

## Quality Bar

- Keep bullets high signal. Do not rewrite the whole source as a compressed transcript.
- Make todos actionable enough that the user can start work later without rereading everything.
- Preserve named references, commands, URLs, libraries, products, people, and RFCs.
- If source access is partial, say exactly what was available and what was missing.
- Use citations or source anchors when available: URLs, page numbers, timestamps, headings, slide numbers, or file paths.

## Reading Guide

| Situation | Read |
| --- | --- |
| Need to access or normalize a resource | `references/intake.md` |
| Need to decide what counts as a topic, idea, research lead, or todo | `references/synthesis.md` |
| Need to save or export the notes | `references/output-formats.md` |
| The source is messy, partial, long, visual, or transcript-only | `references/gotchas.md` |
| Need a reusable output skeleton | `templates/reading-notes.md` |

## Gotchas

1. A transcript is not the whole talk. Demos, slides, diagrams, code, and audience questions can carry important context.
2. Messy live notes are evidence, not a complete source. Keep uncertainty visible.
3. A vague todo like "research ClickHouse" is weak. Prefer "Compare ClickHouse MergeTree primary key design against common Nightwatch dashboard queries."
4. Interesting does not mean merely mentioned. Promote items that are surprising, useful, controversial, reusable, or connected to later action.
5. Do not ask about export format before producing the notes unless the user's main request is file creation.

## Verification Notes

The helper script is deterministic and only classifies source descriptors. It does not fetch content or summarize. Verify command syntax with `--help` and package behavior with `scripts/test_skill.py`.
