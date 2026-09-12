# Repo Intent Documenter

Production skill for creating evidence-backed repository intent documents that make project purpose and unresolved questions obvious to future coding agents.

## What It Covers

- repository inspection for docs, manifests, source entrypoints, tests, CI, and agent instructions
- confidence-labeled intent claims with evidence anchors
- `REPO_INTENT.md` drafting and update workflow
- targeted user questions for unclear purpose, scope, and non-goals
- deterministic inventory script and validation suite

## Key Files

- `SKILL.md` for the authoritative instructions
- `references/methodology.md` for inspection and evidence rules
- `references/document-contract.md` for output shape and review workflow
- `references/gotchas.md` for common failure modes
- `templates/repo-intent.md` for the default document shell
- `scripts/repo_intent_inventory.py` for a first-pass repository inventory
