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

1. Read the source context and decide whether the item should remain the default `Product Backlog Item` or become an explicit `Epic`, `Feature`, `User Story`, `Task`, `Issue`, or `Bug`.
2. Run `python3 scripts/create_work_item_packet.py --title "<title>"` from the current working directory for the default PBI.
3. Add `--type <type>` only when the user specifies or clearly needs another work item type.
4. Add `--context-file /path/to/file.md` when the source notes already exist on disk.
5. Open the generated `work-item.md` and replace the placeholders with a final audience-safe draft.
6. Keep spillover notes, raw reproduction details, design scraps, or open questions in `context.md`.

## Recommended Command Patterns

| Need | Command |
| --- | --- |
| Create the default PBI packet beside the command | `python3 scripts/create_work_item_packet.py --title "Add billing status to account summary"` |
| Seed the packet from saved notes | `python3 scripts/create_work_item_packet.py --type bug --title "CSV export fails for long date ranges" --context-file ./notes/csv-export-bug.md` |
| Save to an explicit visible folder | `python3 scripts/create_work_item_packet.py --type issue --title "Vendor certificate blocks go-live" --save-root ./work-items` |

## Writing Contract

- Do not use `#`, `##`, or `###` headings in `work-item.md`.
- Use bold section labels in `work-item.md`.
- Use these exact labels for non-bug drafts, in this order:
  1. `**Title**`
  2. `**Problem**`
  3. `**Action**`
  4. `**Outcome**`
  5. `**Acceptance Criteria**`
  6. `**Developer Notes**`
  7. `**Test Scenario**`
- For `Bug`, add `**Reproduction Steps**` between `**Problem**` and `**Action**`.
- Prefer short paragraphs, bullets, and numbered lists.
- Write for technical and non-technical readers at the same time. The first paragraph should make sense without product or codebase trivia.
- Default unspecified work to `Product Backlog Item`; use `Bug`, `Feature`, `Task`, and other types only when specified or clearly required.
- `Feature` drafts should keep `Problem` and `Outcome` to one or two short paragraphs each, with no more than five high-level actions.
- `Bug` drafts must include simple numbered `**Reproduction Steps**` that QA, product, or developers can follow without interpreting dense prose.
- `User Story` drafts should describe who needs what and why before implementation notes.
- `Task` drafts should stay execution-focused and should not masquerade as user-facing value.
- `Developer Notes` is for implementation constraints, dependencies, rollout notes, environment notes, and known unknowns. Keep it bullet-based.
- `Test Scenario` is for QA-facing validation notes. Use bullets unless the user supplies a more structured scenario.

## What Goes Where

Put these in `work-item.md`:

- the concise title
- the audience-safe problem statement
- reproduction steps for bugs
- the high-level action
- the intended outcome
- acceptance criteria
- developer notes that materially guide delivery
- QA-specific test scenario notes

Put these in `context.md`:

- raw notes or copied source text
- assumptions and missing details
- implementation specifics that would distract from the main work item
- long reproduction notes, logs, or supporting details

Put these in `metadata.json`:

- the chosen type and process assumption
- the title and slug
- the packet path
- the official sources used to guide the draft
