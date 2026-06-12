---
name: oneshot-websites
description: "Generate semi-deterministic catalogs of parallel one-shot single-file website variants for repertoire, benchmark, model showcase, many-style, PROMPT.md route, or harness-parallel workflows. Do NOT use for a normal single landing page."
---

# Oneshot Websites

Create a benchmark-ready directory of one-shot single-file website variants, each with its own `PROMPT.md`, `index.html`, route path, style type, and catalog entry.

## Decision Tree

What is the user asking for?

- Full repertoire or benchmark catalog -> generate every style in `references/repertoire.md`, then build a root catalog from `references/catalog-index.md`.
- A subset of styles -> use the selection rules in `references/generation-protocol.md`, then generate only those style routes.
- A new or custom style family -> read `references/ui-guidance.md`, add a temporary style brief, and keep the catalog schema unchanged.
- A single one-shot website -> use the same `PROMPT.md` and quality rules, but make one route only and skip the full catalog unless requested.
- A generated catalog needs checking -> run `scripts/validate_catalog.py` against the output directory.

## Quick Reference

| Task | Do this |
| --- | --- |
| Generate the default showcase | Create all 11 routes from `references/repertoire.md` under one output directory. |
| Generate N variants | Use deterministic seed selection from `references/generation-protocol.md`. |
| Write each route prompt | Start from `templates/PROMPT.md` and fill the style-specific brief. |
| Coordinate parallel work | Give each worker only `agents/variant-worker.md`, the assigned style, and the shared quality bar. |
| Build the directory index | Use `scripts/build_catalog_index.py` or follow `references/catalog-index.md`. |
| Validate a generated catalog | Run `python3 scripts/validate_catalog.py <output-dir>`. |

## Default Output Contract

Create one directory with this shape:

```text
oneshot-websites/
  index.html
  manifest.json
  restaurant/
    PROMPT.md
    index.html
  perfume/
    PROMPT.md
    index.html
  ...
```

Each route is a static single-file HTML artifact. The root `index.html` lists every route with path, experience link, `PROMPT.md` link, one-shot website type, status, and summary.

## Parallel Harness Contract

Leave execution mechanics to the active harness. If it supports subagents or parallel jobs, fan out one worker per style. If it does not, run the workers sequentially while preserving isolated instructions and outputs.

Use these invariants either way:

1. Plan the manifest before generating variants.
2. Give each worker one style and no sibling route outputs.
3. Produce `PROMPT.md` before `index.html` for each route.
4. Keep every route single pass for benchmark fairness unless the user explicitly requests curation.
5. Preserve failed or partial routes in the manifest with a non-OK status instead of silently replacing them.
6. Build the catalog after all routes finish.

## Reading Guide

| Need | Read |
| --- | --- |
| Style list and deterministic slugs | `references/repertoire.md` |
| Parallel planning, seed rules, output schema | `references/generation-protocol.md` |
| Directory index, fairness note, manifest fields | `references/catalog-index.md` |
| UI style-brief quality and variation language | `references/ui-guidance.md` |
| Single-file HTML constraints and checks | `references/quality-bar.md` |

## Gotchas

- Do not let later route workers see earlier route outputs when the catalog is being used as a model comparison. Shared context contaminates the benchmark.
- Do not retry a failed route by default. If retries are allowed, mark the catalog as curated rather than single-pass.
- Do not build one visual system and recolor it 11 times. Each style needs a distinct layout, type strategy, motion signature, and atmospheric device.
- Do not hide `PROMPT.md`. The catalog is useful because every artifact exposes the prompt that produced it.
- Do not depend on external images or frameworks for route visuals. Use CSS, inline SVG, canvas, generated geometry, and vanilla JavaScript.

## Validation

For this skill package:

```bash
python3 skills/oneshot-websites/scripts/validate.py skills/oneshot-websites
python3 skills/oneshot-websites/scripts/test_skill.py skills/oneshot-websites
```

For a generated catalog:

```bash
python3 skills/oneshot-websites/scripts/validate_catalog.py path/to/oneshot-websites
```
