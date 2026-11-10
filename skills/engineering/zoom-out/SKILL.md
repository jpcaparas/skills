---
name: zoom-out
description: "Maps unfamiliar code one layer up: modules, callers, callees, entrypoints, boundaries and data flow. Use for 'zoom out', call graph, module map, 'who calls this', or orientation before editing. Not for line-by-line explanation or already-scoped bug fixes."
compatibility: "Optional helper script needs python3; rg and git improve discovery."
---

# zoom-out

Give a grounded map of an unfamiliar code area before implementation or detailed explanation: who defines, orchestrates and exposes the behaviour, one layer up and one layer down. Stop there; expanding until every dependency appears makes the map useless.

## How

- Restate the target concretely (symbol, path, route, job, feature). If it cannot be inferred, ask one concise question. If a feature has no obvious entrypoint, find handles first: routes, commands, jobs, public exports, UI screens, handlers, tests, migrations, manifests, then exact identifiers, route segments, config keys, table, queue and event names.
- Upstream: callers, routes, commands, jobs, subscribers, tests, screens, public exports. Downstream: services, data access, adapters, external APIs, queues, stores, feature flags, config. Group files by responsibility, not by directory.
- `python3 scripts/zoom_out_inventory.py --repo <repo> --target "<symbol-or-path>" [--json]` produces candidate centre files, caller candidates, import edges and suggested reads. It is a lead generator, not proof; skip it when the target is known or a focused search is enough.
- A textual match is a lead, not a caller. Call a path verified only after confirming the import, registration, route, test or runtime wiring, and label the rest "likely, not verified". Dynamic systems hide paths in config, decorators, DI containers, generated code, queues and framework registration; list those as unknowns instead of smoothing over them. If no callers or tests turn up in the inspected scope, say so rather than expanding to fill a quota.
- A directory tree is not an architecture map.

## Answer

Compact, not every file found. Use the parts that help: target, responsibility-grouped map, caller paths, callees and dependencies, boundaries crossed (package, process, network, persistence, framework), evidence (paths, symbols, queries), unknowns, and the shortest ordered next-reads list (exactly as many files as the user asked for). If the user wants teaching afterwards, hand the map to `eli12`; for pure text search or counting use `ripgrep`; for a bug fix with an unclear edit target, zoom out briefly, then return to normal coding. This maps code topology, not product intent.
