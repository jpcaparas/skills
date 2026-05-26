# Resource Intake

Use this reference to gather grounded source material before synthesizing reading notes.

## Intake Principles

1. Prefer primary source content over summaries of the source.
2. Capture provenance before synthesis: title, URL/path, author or speaker, event, publication date when visible, and access limitations.
3. Preserve structure where it helps: headings, timestamps, slide numbers, page numbers, speaker turns, and code blocks.
4. Normalize noisy text lightly. Fix obvious OCR or transcript artifacts only when meaning is clear.
5. Stop and disclose when access is partial. Do not invent the missing parts.

## Source Types

| Source | First move | Watch for |
| --- | --- | --- |
| Pasted notes | Use the text directly and infer sections from headings and indentation | Incomplete context, shorthand, personal todos mixed with talk content |
| Markdown or text file | Read the file and retain headings, links, code blocks, and list nesting | Generated boilerplate, copied snippets without source context |
| PDF or DOCX | Extract text with available document tools; inspect images or pages when visual layout matters | Footnotes, sidebars, tables, screenshots, page-order issues |
| Slide deck | Use slide titles as topic anchors; inspect diagrams and speaker notes when available | Slides often omit spoken rationale |
| Screenshot or image | Use native image analysis where available; capture visible text and layout | Cropped images, tiny text, missing prior/next slide |
| Web URL | Fetch the readable page, title, author, date, and URL; avoid broad crawls unless the task needs them | Cookie walls, dynamic content, stale cached copies |
| YouTube or video URL | Prefer captions/transcript, then metadata and user notes; use timestamps as anchors when available | Transcript errors, missing demos, no slide context |
| Audio or meeting recording | Transcribe or use provided transcript; preserve speaker labels when relevant | Homophones, missed jargon, no visual context |
| Code/RFC/spec | Preserve section numbers, commands, APIs, and examples | Over-summarizing normative language |

## Large Resource Strategy

For long resources, do not load everything into one undifferentiated summary.

1. Split by natural boundaries: heading, page, slide, timestamp, chapter, agenda item, or speaker.
2. Make a temporary map of section titles and one-line content.
3. Mark sections with high follow-up value: named references, commands, claims, warnings, decisions, and unresolved questions.
4. Synthesize across chunks after mapping. Avoid producing isolated chunk summaries unless the user asks.

## Access Failures

When the resource cannot be accessed:

- Say what was attempted and what failed.
- Use any user-provided notes or metadata as the only source.
- Ask for the missing asset in the smallest useful form: transcript, pasted notes, PDF export, screenshots, or the relevant excerpt.
- Still produce a partial homework list when the supplied material supports one.

## Visual Material

For slides, screenshots, whiteboards, or diagrams:

- Inspect the image directly with the host agent's native image capability when available.
- Extract visible text, but also describe relationships, layout, arrows, tables, charts, and highlighted regions.
- Do not treat OCR output as complete when diagrams or code screenshots matter.
- If text is unreadable, ask for a higher-resolution image or original deck after producing what can be grounded.

## Video Notes

For talks, webinars, and tutorials:

- Use timestamps for major sections when available.
- Separate spoken content, demo observations, chat or Q&A, and user notes.
- Preserve named tools, packages, commands, RFCs, links, and book/paper recommendations.
- Mark content inferred from metadata as metadata, not as talk content.

## Conference And Live Notes

Live notes often contain shorthand and personal reminders. Treat them as mixed evidence:

- Promote headings into topics.
- Keep bullets under the most likely topic unless they clearly belong elsewhere.
- Convert "turn this into a skill", "try this", "look up X", and similar fragments into todos.
- Add open questions where the shorthand is ambiguous.
- Avoid over-polishing. The goal is later recall and action, not a perfect article.
