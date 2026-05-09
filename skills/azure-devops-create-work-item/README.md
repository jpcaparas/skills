# azure-devops-create-work-item

Production skill for drafting local Azure DevOps work item packets from loose context using official Azure Boards work item primitives.

## What It Covers

- Product Backlog Item by default, with explicit support for `Epic`, `Feature`, `User Story`, `Task`, `Issue`, and `Bug`
- Deterministic packet creation in the caller's current directory
- Reusable per-type Markdown templates using the standard schema, with dedicated `Reproduction Steps` for bugs
- Mixed-audience writing guidance for work item drafts

## Key Files

- `SKILL.md` - authoritative instructions
- `references/official-primitives.md` - official Azure Boards type semantics and process notes
- `references/output-packet.md` - folder layout and writing contract
- `references/gotchas.md` - classification and formatting traps
- `templates/*.md` - per-type work item templates
- `scripts/create_work_item_packet.py` - helper that creates the local packet scaffold
