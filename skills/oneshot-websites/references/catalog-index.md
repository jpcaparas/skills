# Catalog Index

## Table of Contents

- [Purpose](#purpose)
- [Required Content](#required-content)
- [Visual Direction](#visual-direction)
- [Fairness Note](#fairness-note)
- [Table Columns](#table-columns)
- [Generated Index Script](#generated-index-script)

## Purpose

The root `index.html` is the directory for the run. It should expose what was generated, where each route lives, which `PROMPT.md` produced it, and what one-shot website type was used.

## Required Content

Include these elements:

- A compact hero with catalog title, model or harness name, route count, generated date, and project name.
- A visible fairness note near the top.
- A responsive table or table-like list of routes.
- Links to each route and its `PROMPT.md`.
- Status chips for OK, partial, or failed routes.
- A short summary per route.

## Visual Direction

Use a restrained catalog look rather than a marketing page:

- Warm off-white background, ink text, muted dividers, and one calm accent.
- Dense but readable information layout.
- Rounded panels are acceptable, but keep the index utilitarian and scannable.
- On mobile, collapse table rows into labeled blocks with the same information.
- Avoid decorative hero art. The generated routes are the showcase; the index is navigation.

## Fairness Note

Use a note equivalent to this, adapted to the actual harness and model:

```text
Each one-shot showcase and its paired PROMPT.md were generated in an isolated route context so sibling runs do not influence one another. Route generation is single-pass: no retries were attempted for failures, odd behavior, or output quirks. This keeps the catalog fair as a model-comparison surface and shows how the model performs out of the box.
```

If any route was repaired, replace "single-pass" with "curated" and disclose what changed.

## Table Columns

| Column | Content |
| --- | --- |
| Path | Route path such as `/restaurant/`. |
| Experience | Link to the route `index.html`. |
| Prompt | Link to route `PROMPT.md`. |
| Type | Canonical type slug or label. |
| Status | `OK`, `PARTIAL`, `ERROR`, or `CURATED`. |
| Summary | One sentence describing the generated route. |

## Generated Index Script

Prefer the script when the manifest exists:

```bash
python3 skills/oneshot-websites/scripts/build_catalog_index.py \
  --manifest path/to/oneshot-websites/manifest.json \
  --out path/to/oneshot-websites/index.html
```

If the harness cannot run scripts, fill `templates/catalog-index.html` manually from the manifest using the same columns and fairness note.
