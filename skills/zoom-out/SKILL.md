---
name: zoom-out
description: "Map unfamiliar code one layer up: modules, callers, callees, entrypoints, boundaries, dependencies, and data flow. Trigger on zoom out, call graph, module map, architecture map, who calls this, or orientation before edits. Do NOT use for line-by-line explanation or already-scoped bug fixes."
compatibility: "Requires repository/file access. Optional: python3 for scripts/zoom_out_inventory.py and local validators; rg and git improve discovery when available."
metadata:
  version: "1.0.0"
  short-description: "Map unfamiliar code one layer up"
  openclaw:
    category: "development"
    subcategory: "code-understanding"
    requires:
      bins: [python3]
    tags: ["architecture", "call-graph", "codebase", "orientation", "modules"]
references:
  - discovery
  - caller-mapping
  - output-contract
  - gotchas
---

# zoom-out

Create a grounded map of an unfamiliar code area before diving into implementation or detailed explanation.

## Decision Tree

What is the user asking for?

- "Zoom out", "go up a layer", "map the relevant modules and callers", "who calls this", or similar orientation language
  Use this skill. Produce a code context map before making recommendations.

- A specific symbol, file, route, job, table, command, event, or component is named
  Run the inventory helper when possible, then trace direct callers, direct callees, entrypoints, and boundary crossings.

- A feature or subsystem is named, but no concrete entrypoint is obvious
  Find likely entrypoints first: routes, commands, jobs, public exports, UI screens, handlers, tests, migrations, and package manifests.

- The user asks "how does this work?" and wants teaching, not just orientation
  Build the map first if the area is unfamiliar, then use {{ skill:eli12 }} for the final teaching-style explanation.

- The user asks for a bug fix or implementation and the edit target is unclear
  Do a short zoom-out pass first, then switch back to normal coding mode once the relevant surface is known.

- The user only needs a text search, literal occurrence count, or filename lookup
  Use {{ skill:ripgrep }} directly instead of producing an architecture map.

- The user asks for durable repository intent or product purpose documentation
  Use {{ skill:repo-intent-documenter }} instead. This skill maps code topology, not human intent.

## Quick Reference

| Need | Do |
| --- | --- |
| First pass around a symbol or path | `python3 scripts/zoom_out_inventory.py --repo <repo> --target "<symbol-or-path>" --json` |
| Human-readable inventory | `python3 scripts/zoom_out_inventory.py --repo <repo> --target "<symbol-or-path>"` |
| Full discovery method | Read `references/discovery.md` |
| Caller and callee tracing rules | Read `references/caller-mapping.md` |
| Final answer shape | Read `references/output-contract.md` or copy `templates/zoom-out-map.md` |
| Hidden edge cases | Read `references/gotchas.md` |
| Validate the skill package | `python3 scripts/validate.py skills/zoom-out` |
| Run local packaging and probe tests | `python3 scripts/test_skill.py skills/zoom-out` |

## Default Workflow

1. Restate the target in concrete terms: symbol, path, route, feature, job, package, or subsystem.
2. Resolve the repository root and any user-provided scope boundaries. If the target is missing and cannot be inferred from context, ask one concise question.
3. Run `scripts/zoom_out_inventory.py` when local files are available. Treat its output as a lead generator, not proof.
4. Search for the target using exact strings first, then nearby names: exported symbols, filenames, route segments, test names, config keys, table names, queue names, event names, and API paths.
5. Identify the center of gravity: the 3-7 files that define, orchestrate, or expose the behavior.
6. Trace one layer up and one layer down:
   - Upstream: callers, routes, commands, jobs, event subscribers, tests, UI screens, public exports.
   - Downstream: services, data access, adapters, external APIs, queues, stores, feature flags, config.
7. Group files by responsibility, not by directory alone.
8. Mark observation vs inference. If a caller path is based on a textual match, say so until you verify execution wiring.
9. Return a compact map. Do not include every file found.
10. End with the smallest useful next-read list or implementation target if the user plans to edit.

## Output Contract

Use these sections when they help. Omit sections that would add noise.

- **Target** - The symbol, file, route, feature, or subsystem being mapped.
- **One-Layer Map** - A responsibility-grouped map of relevant modules.
- **Caller Paths** - How execution reaches the target from user actions, jobs, commands, tests, or public APIs.
- **Callees And Dependencies** - What the target invokes, persists to, publishes, imports, or delegates to.
- **Boundaries** - Ownership, package, process, network, persistence, or framework boundaries crossed.
- **Evidence** - File paths, symbols, search queries, and commands used.
- **Unknowns** - Dynamic dispatch, generated code, framework registration, or missing runtime evidence.
- **Next Reads** - The shortest ordered list of files to inspect next.

## Reading Guide

| Situation | Read |
| --- | --- |
| Need to find the right entrypoints before tracing | `references/discovery.md` |
| Need to decide what counts as a caller, callee, or boundary | `references/caller-mapping.md` |
| Need a consistent final map with evidence and uncertainty labels | `references/output-contract.md` |
| Results are noisy, missing, dynamic, generated, or framework-driven | `references/gotchas.md` |

## Gotchas

1. A directory tree is not an architecture map. Show responsibilities and execution paths, not just folders.
2. Textual matches are leads, not verified callers. Confirm imports, registration, routes, tests, or runtime wiring before presenting a path as real.
3. Dynamic systems hide call paths in config, decorators, dependency injection containers, generated code, queues, conventions, and framework registration.
4. The useful scope is usually one layer up and one layer down. Expanding until every dependency appears makes the map less useful.
5. Do not erase uncertainty. A precise "likely caller, not verified" is better than a confident but unsupported diagram.

## Helper Scripts

- `scripts/zoom_out_inventory.py` creates a first-pass inventory of candidate center files, caller candidates, import edges, directory clusters, manifests, and suggested reads.
- `scripts/validate.py` checks structure, frontmatter, cross-references, required directories, evals, and Python syntax.
- `scripts/test_skill.py` runs validation, eval coverage checks, cross-reference checks, and a temporary-repo probe for the inventory script.

## Verification Notes

This skill's examples are local commands. Verify command syntax with `--help` and validate behavior by running `scripts/test_skill.py`, which builds a temporary codebase and confirms the inventory helper returns target matches, caller candidates, import edges, and suggested reads.
