# Discovery Method

Use this reference when the target is vague, the repo is unfamiliar, or the first search returns too many files.

## Goal

Find the smallest evidence-backed slice of code that explains where a target lives, who reaches it, and what it touches. The goal is not a complete static analysis report. The goal is a map good enough for a safe next action.

## Target Normalization

Turn the user's language into searchable handles:

| User phrase | Search handles |
| --- | --- |
| Feature name | route segments, UI labels, test names, command names, event names |
| Symbol name | exact identifier, exported aliases, class/function filenames |
| File path | basename, stem, public exports, nearby tests |
| API route | route file, controller, client call sites, OpenAPI entries |
| Background job | scheduler config, queue topic, handler, retry/dead-letter code |
| Database concept | table/model name, migration, repository/DAO, generated types |

Prefer exact searches before fuzzy searches. Fuzzy searches are useful only after the exact handles are exhausted.

## First Pass Commands

Run the helper when the skill files are available:

```bash
python3 scripts/zoom_out_inventory.py --repo <repo> --target "<target>" --json
```

If the helper is not available, use the same shape manually:

```bash
rg -n -F "<target>" <repo>
rg --files <repo> | rg -i "<target-or-path-fragment>"
```

Use {{ skill:ripgrep }} for deeper search flag choices.

## Entry Point Checklist

Look for these before reading deeply:

- routes, controllers, handlers, middleware, resolvers, commands, cron jobs, queue consumers
- public package exports and index files
- UI screens, pages, components, hooks, and event handlers
- tests and fixtures that name the behavior
- migrations, schemas, generated models, API specs, and config files
- package manifests, workspace files, and build config that define boundaries

## Center Of Gravity

A file is likely central when it does at least one of these:

- defines the target symbol or route
- orchestrates multiple lower-level pieces around the target
- owns the public API used by other modules
- bridges across boundaries such as HTTP, queues, persistence, or external services
- appears in focused tests for the target behavior

Avoid promoting a file just because it imports a shared type, constant, or utility.

## Scope Control

Stop expanding when you have:

- the defining file or closest owner
- at least one verified upstream path
- the main downstream dependencies
- the boundary crossings
- tests or fixtures that exercise the behavior
- enough uncertainty labels to avoid pretending the map is complete

If the map is still too broad, narrow by runtime path: web request, background job, CLI command, UI interaction, test case, or package export.

## See Also

- `references/caller-mapping.md` for deciding whether a relationship is a real caller or only a lead.
- `references/output-contract.md` for turning the evidence into a concise final map.
- `references/gotchas.md` for dynamic registration and noisy search recovery.
