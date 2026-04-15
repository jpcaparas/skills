# Output Packet

Use this file when you need the folder layout, command flow, or formatting rules.

## Packet Contract

The packet always lives under the caller's current working directory unless the user provides an explicit visible destination.

Each packet contains:

- `work-item.md` - the main draft intended to be pasted into Azure DevOps
- `context.md` - the extracted or raw source context that informed the draft
- `sources.md` - the official Microsoft Learn links used for type guidance
- `metadata.json` - machine-readable packet metadata

## Workflow

1. Read the source context and decide whether the item is an `Epic`, `Feature`, `User Story`, `Task`, `Issue`, or `Bug`.
2. Run `python3 scripts/create_work_item_packet.py --type <type> --title "<title>"` from the current working directory.
3. Add `--context-file /path/to/file.md` when the source notes already exist on disk.
4. Open the generated `work-item.md` and replace the placeholders with a final audience-safe draft.
5. Keep spillover notes, raw reproduction details, design scraps, or open questions in `context.md`.

## Recommended Command Patterns

| Need | Command |
| --- | --- |
| Create the default packet beside the command | `python3 scripts/create_work_item_packet.py --type feature --title "Add billing status to account summary"` |
| Seed the packet from saved notes | `python3 scripts/create_work_item_packet.py --type bug --title "CSV export fails for long date ranges" --context-file ./notes/csv-export-bug.md` |
| Save to an explicit visible folder | `python3 scripts/create_work_item_packet.py --type issue --title "Vendor certificate blocks go-live" --save-root ./work-items` |

## Writing Contract

- Do not use `#`, `##`, or `###` headings in `work-item.md`.
- Use bold section labels such as `**Problem**`, `**Action**`, and `**Outcome**`.
- Prefer short paragraphs, bullets, and numbered lists.
- Write for technical and non-technical readers at the same time. The first paragraph should make sense without product or codebase trivia.
- `Feature` drafts should keep `Problem` and `Requirements/Solution` to at most three short paragraphs each, with no more than five high-level actions.
- `Bug` drafts must include `**Reproduction steps**` with enough detail that another person can reproduce the behavior and understand the expected result.
- `User Story` drafts should describe who needs what and why before any implementation talk.
- `Task` drafts should stay execution-focused and should not masquerade as user-facing value.

## What Goes Where

Put these in `work-item.md`:

- the concise title
- the audience-safe problem statement
- the high-level solution or action
- the intended outcome
- acceptance criteria when the type calls for it

Put these in `context.md`:

- raw notes or copied source text
- assumptions and missing details
- implementation specifics that would distract mixed audiences
- long reproduction notes, logs, or supporting details

Put these in `metadata.json`:

- the chosen type and process assumption
- the title and slug
- the packet path
- the official sources used to guide the draft
