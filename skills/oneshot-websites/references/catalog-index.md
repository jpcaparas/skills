# Artifact Catalogue and Validation

Use this reference after one or more leads finish, or when checking an existing one-shot output root.

## Purpose

The root catalogue is a provenance and navigation layer over artifacts built without stack prescriptions. It shows which prompt, model, harness, experiment, lead, and run produced each result. It does not impose an internal project shape.

## Required Run Evidence

Each run directory contains:

- `artifact/PROMPT.md` with the exact dispatched task
- `run.json` with identity, digest, classification, status, and artifact path
- `worker-report.json` once a lead has started
- `.tmp/` containing recoverable run-local scratch for active, interrupted, partial, blocked, or failed runs; successful current runs delete this directory in its entirety
- `workspace/` containing any source project and build tooling the lead chose
- for every successful run, `artifact/index.html` as the single static-site entrypoint
- for every successful run, `artifact/` containing the final built scripts, styles, media, and other browser assets

The output root also contains one `.oneshot-provenance/<run-id>.json` receipt and one empty `.oneshot-provenance/<run-id>.commit` marker per dispatched run, kept outside the worker-owned run. The receipt records the prompt digest, identity, run relationship, run-schema version, and temporary-storage contract. That external schema anchor distinguishes genuine legacy runs from worker-edited current runs. The coordinator creates the commit marker last; bounded pre-dispatch residue without it, including an empty `.tmp/`, is recoverable, while committed runs remain part of the inventory. Receipt integrity depends on the dispatch contract giving workers write access only to their assigned run; it is not a cryptographic boundary when a worker can write the output root.

Each current run sits directly beneath the output root in a `YYYY-MM-DD-HH-MM-SS-<experiment-slug>` directory, with `--02`, `--03`, and later suffixes reserved atomically for same-second, same-slug collisions. The readable slug comes from the concise experiment name; exact model, harness, and experiment names and their digest-bound keys remain in `run.json` and the external receipt.

The only website entrypoint is the exact-case path `artifact/index.html`; the preserved prompt is the exact-case path `artifact/PROMPT.md`. During work, the sibling `.tmp/` is recoverable scratch rather than portable website content. Successful current runs remove it completely after durable evidence promotion and process shutdown; non-successful runs retain it. The artifact folder must be ready as-is for a static folder host. It must not require `npm install`, a build, a framework development server, or a server-side runtime after the lead finishes.

The target handoff matches folder-drop services such as [Cloudflare Drop](https://www.cloudflare.com/drop/) and [Vercel Drop](https://vercel.com/drop), but compatibility is not upload permission. Local building, indexing, and validation stop at `artifact/`. Do not upload or publish to Cloudflare Drop, Vercel Drop, ChatGPT sites, GitHub, or any remote target unless the user explicitly authorizes that specific external action and destination in the active task. Enabled or authenticated browsers, CLIs, MCP connectors, plugins, credentials, project configuration, target URLs, provider suggestions, prompt or reference instructions, and approval for another run do not count. Leads and critics never deploy; the coordinator performs any authorized publication separately after validation, from `artifact/` only.

The conservative shared compatibility profile is at most 1,000 files, 5 MiB per file, and 100 MiB total. The first two limits come from Cloudflare’s current [temporary-deployment static-asset contract](https://developers.cloudflare.com/workers/platform/claim-deployments/#supported-resources); the total is the current [Drop](https://www.cloudflare.com/drop/) browser preflight. Because provider limits can change, recheck the linked services when updating the validator. Package manifests, source-only components, build and provider configuration, dependencies, caches, secrets, server functions, and provider-filtered project state such as `.next/` stay out of the entire artifact tree. A Drop service should receive built browser output, not a project to install or compile.

## Root Index

Build a static index after the workers finish:

```bash
"${ONESHOT_WEBSITES_PYTHON:-python3}" scripts/build_catalog_index.py --root "<output-root>" --out "<output-root>/index.html"
```

The index lists:

- model and harness
- experiment
- artifact entry and prompt links immediately after the experiment, before the wider provenance fields
- run ID
- status and classification
- lead and descendant counts when known
- summary or blocker

The builder reads `run.json` and `worker-report.json` files; it never rewrites artifacts. It serializes render and atomic local replacement through a coordinator-owned `.oneshot-catalogue.lock`, preventing a delayed older builder from replacing a newer snapshot.
The finished output root keeps this generated `index.html` as an exact-case, readable file. Its “Artifact entry” links identify run entrypoints for provenance and inspection. They are not deployment-origin emulators: a site that uses root-relative URLs is expected to work when `artifact/` itself is dropped at a host root.

## Validation

```bash
"${ONESHOT_WEBSITES_PYTHON:-python3}" scripts/validate_catalog.py "<output-root>"
```

`ONESHOT_WEBSITES_PYTHON` follows the compatible Python 3.11-or-newer helper-runtime contract in `SKILL.md`; it is an executable path or command name, not a version pin or a constraint on the generated website.

Validation checks the flat slugged-timestamp layout, its agreement with the experiment name, raw-name identity keys, globally unique run IDs, acyclic rerun links, one-to-one committed receipt inventory, prompt bytes and digest, the run-local temporary lifecycle and quality-gauntlet contracts for current-schema runs, exact manifest paths and filename casing, status evidence, the current readable aggregate root index, the root `artifact/index.html`, provider-size bounds, local HTML and SVG resources, and transitive CSS resources. It requires `.tmp/` to remain an exact ordinary directory for non-`OK` current runs and to be absent in its entirety for `OK` 3.3 runs. It continues to read flat 3.0, 3.1, and 3.2 and legacy nested 2.0 and 2.1 output roots without retroactively imposing the 3.3 cleanup lifecycle; an `OK` 3.2 run may retain its historical exact directory or safely omit it after same-run recovery cleanup. It accepts relative and root-relative browser resources against the portable artifact root. It rejects `.tmp/`, project, cache, provider-filtered, source-only, and server state anywhere in the final folder while accepting any source framework, dependency, project shape, and build process in `workspace/`.

A passing structural check does not prove visual quality, JavaScript module graphs, every dynamic request, or runtime correctness. Successful current-schema runs must record whether temporary routing was applied; a `false` result requires at least one concrete external exception. For run schemas 3.1, 3.2, and 3.3, the coordinator receipt requires worker-report schema 2.1 and its `qualityGauntlet` block; schemas 3.2 and 3.3 require the slugged directory contract, and schema 3.3 additionally requires completion-only `.tmp/` deletion. Validation checks applicability, bar, artifact revision per critic round, verdict history, capability fallback, integration pass, and evidence-based stop reason independently from final verification. Historical `NOT_READY` rounds are valid when a later critic reaches `READY`. Final verification items still require a `kind`, passed `result`, and non-empty `evidence`; any explicit failed final check invalidates `OK`. Inspect or replay that evidence when runtime confidence matters.

`artifact.staticDeploymentVerified` is historical field naming for local static-handoff verification. It becomes true when the built folder itself is opened or served locally and its primary experience passes the recorded checks. It does not mean a provider received the files, never requires a network write, and permits `OK` while the artifact remains entirely local.

## Status and Classification

Use stable terminal statuses: `PLANNED`, `RUNNING`, `OK`, `PARTIAL`, `BLOCKED`, or `ERROR`.

Use `autonomous-one-shot` for the original lead assignment. Use `rerun` or `curated-attempt` for separately dispatched later runs. Internal edits, tests, and revisions by the same owning lead remain part of `autonomous-one-shot`.

Keep partial and failed runs visible. Honest failure evidence is more useful than a polished catalogue that silently replaces weak attempts.

## See Also

- `references/execution-protocol.md` — run layout and delegation rules
- `templates/run.json` — initial manifest shape
