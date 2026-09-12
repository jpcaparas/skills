# Output Formats

Use this reference when the user wants notes saved, exported, converted, or shared.

## Default Behavior

Produce the notes in Markdown first unless the user already requested a specific file format. After the notes, ask a short export question:

```text
Want me to save this as Markdown, DOCX, PDF, or another format?
```

If the user already specified a format, create that format without asking again.

## Format Choices

| Format | Use when | Notes |
| --- | --- | --- |
| Markdown | The user wants durable notes, easy editing, git storage, or copy-paste reuse | Default format |
| DOCX | The user wants a shareable document or later Word/Google Docs editing | Keep headings and checkboxes readable |
| PDF | The user wants a fixed review artifact | Generate from Markdown or DOCX when tooling is available |
| CSV | The user wants only todos or research leads imported elsewhere | Columns work better than prose |
| XLSX | The user wants sortable homework, priorities, statuses, and due dates | Use a spreadsheet tool when available |
| JSON | The user wants machine-readable notes for another workflow | Keep schema simple and explicit |

## Suggested Filenames

Prefer predictable, repo-agnostic filenames:

- `reading-notes-YYYY-MM-DD.md`
- `<event-or-resource-slug>-reading-notes.md`
- `<talk-title-slug>-homework.md`
- `<resource-slug>-todos.csv`

Avoid hard-coded machine paths. Save in the current workspace or a user-specified destination.

## Markdown Contract

Use `templates/reading-notes.md` for saved Markdown. Keep headings stable so the notes can be appended to a daily journal or converted later.

## DOCX And PDF

When document tooling is available:

1. Generate the Markdown version first.
2. Convert headings, checkboxes, links, and tables cleanly.
3. Preserve source metadata near the top.
4. Use readable page breaks only for long notes.
5. Verify the file exists and can be opened or rendered.

If no conversion tooling is available, save Markdown and explain that DOCX/PDF conversion was not available in the current environment.

## Todo-Only Export

When the user asks for a task list, export only actionable items.

Recommended CSV columns:

```csv
status,type,priority,task,source,notes
todo,research,P2,"Read the PHP generics RFC","Laracon Live JP 2026","Focus on syntax and runtime erasure tradeoffs"
```

Use priority only when it is inferable or requested. Do not invent due dates.

## Append Mode

For ongoing conferences or long study sessions:

- Preserve the existing file structure.
- Append a new dated or talk-specific section.
- De-duplicate research leads.
- Keep completed todos intact unless the user asks to clean them up.
