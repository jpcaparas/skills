# zoom-out

Installable skill for mapping unfamiliar code one layer up: relevant modules, callers, callees, entrypoints, dependencies, boundaries, evidence, and next reads.

## What it covers

- code orientation before editing or detailed explanation
- caller and callee maps around a symbol, file, route, job, feature, or subsystem
- responsibility-grouped module maps with verified vs inferred relationships
- dynamic-registration and framework-wiring caveats
- a deterministic first-pass inventory helper for local repositories

## Key files

- `SKILL.md` - authoritative routing and workflow
- `references/discovery.md` - target discovery and scope control
- `references/caller-mapping.md` - caller/callee evidence rules
- `references/output-contract.md` - final response shape
- `references/gotchas.md` - common mapping failure modes
- `scripts/zoom_out_inventory.py` - first-pass inventory helper
