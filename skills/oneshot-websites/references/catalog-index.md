# Artifact Catalogue and Validation

Use this reference after one or more leads finish, or when checking an existing one-shot output root.

## Purpose

The root catalogue is a provenance and navigation layer over artifacts built without stack prescriptions. It shows which prompt, model, harness, experiment, lead, and run produced each result. It does not impose an internal project shape.

## Required Run Evidence

Each run directory contains:

- `artifact/PROMPT.md` with the exact dispatched task
- `run.json` with identity, digest, classification, status, and artifact path
- `worker-report.json` once a lead has started
- `workspace/` containing any source project and build tooling the lead chose
- for every successful run, `artifact/index.html` as the single static-site entrypoint
- for every successful run, `artifact/` containing the final built scripts, styles, media, and other browser assets

The output root also contains one `.oneshot-provenance/<run-id>.json` receipt and one empty `.oneshot-provenance/<run-id>.commit` marker per dispatched run, kept outside the worker-owned run. The receipt records the prompt digest, identity, and run relationship. The coordinator creates the commit marker last; bounded pre-dispatch residue without it is recoverable, while committed runs remain part of the inventory. Receipt integrity depends on the dispatch contract giving workers write access only to their assigned run; it is not a cryptographic boundary when a worker can write the output root.

Each model, harness, and experiment namespace contains an exact-case `.oneshot-identity.json` marker that binds its derived key to the exact raw name. The validator cross-checks these coordinator-owned markers against every run so distinct identities never silently share a namespace.

The only website entrypoint is the exact-case path `artifact/index.html`; the preserved prompt is the exact-case path `artifact/PROMPT.md`. The artifact folder must be deployable as-is to a static folder host. It must not require `npm install`, a build, a framework development server, or a server-side runtime after the lead finishes.

The target handoff matches folder-drop services such as [Cloudflare Drop](https://www.cloudflare.com/drop/) and [Vercel Drop](https://vercel.com/drop): upload `artifact/` itself, not the source workspace. Deployment is a separate external action and occurs only when the user asks for it.

The conservative shared compatibility profile is at most 1,000 files, 5 MiB per file, and 100 MiB total. The first two limits come from Cloudflare’s current [temporary-deployment static-asset contract](https://developers.cloudflare.com/workers/platform/claim-deployments/#supported-resources); the total is the current [Drop](https://www.cloudflare.com/drop/) browser preflight. Because provider limits can change, recheck the linked services when updating the validator. Package manifests, source-only components, build and provider configuration, dependencies, caches, secrets, server functions, and provider-filtered project state such as `.next/` stay out of the entire artifact tree. A Drop service should receive built browser output, not a project to install or compile.

## Root Index

Build a static index after the workers finish:

```bash
"${ONESHOT_WEBSITES_PYTHON:-python3}" scripts/build_catalog_index.py --root "<output-root>" --out "<output-root>/index.html"
```

The index lists:

- model and harness
- experiment and run ID
- status and classification
- link to the preserved actual prompt
- links to `artifact/index.html` and `artifact/PROMPT.md`
- lead and descendant counts when known
- summary or blocker

The builder reads `run.json` and `worker-report.json` files; it never rewrites artifacts. It serializes render and atomic publication through a coordinator-owned `.oneshot-catalogue.lock`, preventing a delayed older builder from replacing a newer snapshot.
The finished output root keeps this generated `index.html` as an exact-case, readable file. Its “Artifact entry” links identify run entrypoints for provenance and inspection. They are not deployment-origin emulators: a site that uses root-relative URLs is expected to work when `artifact/` itself is dropped at a host root.

## Validation

```bash
"${ONESHOT_WEBSITES_PYTHON:-python3}" scripts/validate_catalog.py "<output-root>"
```

`ONESHOT_WEBSITES_PYTHON` follows the compatible Python 3.11-or-newer helper-runtime contract in `SKILL.md`; it is an executable path or command name, not a version pin or a constraint on the generated website.

Validation checks namespace order, raw-name identity keys, globally unique run IDs, acyclic rerun links, one-to-one committed receipt inventory, prompt bytes and digest, exact manifest paths and filename casing, status evidence, the current readable aggregate root index, the root `artifact/index.html`, provider-size bounds, local HTML and SVG resources, and transitive CSS resources. It accepts relative and root-relative browser resources against the deployed artifact root. It rejects project, cache, provider-filtered, source-only, and server state anywhere in the final folder while accepting any source framework, dependency, project shape, and build process in `workspace/`.

A passing structural check does not prove visual quality, JavaScript module graphs, every dynamic request, or runtime correctness. Successful runs must also carry concrete worker verification evidence with a `kind`, passed `result`, and non-empty `evidence`; any explicit failed check invalidates `OK`. Inspect or replay that evidence when runtime confidence matters.

## Status and Classification

Use stable terminal statuses: `PLANNED`, `RUNNING`, `OK`, `PARTIAL`, `BLOCKED`, or `ERROR`.

Use `autonomous-one-shot` for the original lead assignment. Use `rerun` or `curated-attempt` for separately dispatched later runs. Internal edits, tests, and revisions by the same owning lead remain part of `autonomous-one-shot`.

Keep partial and failed runs visible. Honest failure evidence is more useful than a polished catalogue that silently replaces weak attempts.

## See Also

- `references/execution-protocol.md` — namespace and delegation rules
- `templates/run.json` — initial manifest shape
