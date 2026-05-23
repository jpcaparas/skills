# Generation Protocol

## Table of Contents

- [Run Modes](#run-modes)
- [Semi-Deterministic Planning](#semi-deterministic-planning)
- [Parallel Worker Contract](#parallel-worker-contract)
- [Manifest Schema](#manifest-schema)
- [Directory Rules](#directory-rules)
- [Failure Policy](#failure-policy)

## Run Modes

| Mode | Trigger | Output |
| --- | --- | --- |
| Full repertoire | "all", "repertoire", "catalog", "benchmark" | All 11 canonical styles. |
| Counted subset | "make 3", "generate 5 variants" | Deterministic subset from the canonical style order. |
| Named subset | Explicit style names or slugs | Only the requested styles, preserving slug names. |
| Custom extension | A new style family or theme | Canonical styles plus custom route briefs if requested. |
| Single route | One website only | One route with `PROMPT.md` and `index.html`; catalog optional. |

## Semi-Deterministic Planning

Before workers start, create a manifest plan. This makes the run repeatable even if the harness decides how to parallelize.

Use this selection algorithm for counted subsets:

1. Normalize the seed as `model-name + requested-theme + current-date`.
2. Hash the normalized seed with any stable local method available to the harness.
3. Walk the canonical style list from the hash offset.
4. Alternate Tier 1 and Tier 2 when possible.
5. Stop after the requested count.

If hashing support is awkward, use the canonical order and record `"selection": "canonical-order"` in the manifest. Do not invent random route names after generation starts.

## Parallel Worker Contract

Each worker receives only:

- `agents/variant-worker.md`
- The assigned style card from `references/repertoire.md`
- The quality rules from `references/quality-bar.md`
- The filled brief in `templates/variant-brief.md`
- The target output path

The coordinator keeps:

- The full manifest
- Catalog-index instructions
- Validation scripts
- Status tracking for each route

The worker writes `PROMPT.md` first, then `index.html`. The coordinator should not rewrite a route to make it match siblings unless the user has explicitly moved from benchmark mode to curated mode.

## Manifest Schema

Write `manifest.json` at the catalog root.

```json
{
  "catalogTitle": "Oneshot Websites",
  "harness": "OpenCode",
  "generated": "2026-05-23",
  "mode": "single-pass",
  "selection": "all-canonical",
  "fairness": "isolated route context; no retries unless marked curated",
  "items": [
    {
      "path": "restaurant/",
      "title": "Maison Vorieux",
      "prompt": "restaurant/PROMPT.md",
      "type": "restaurant",
      "typeLabel": "Elegant Restaurant",
      "status": "OK",
      "summary": "Fine dining storefront with candlelit course reveals."
    }
  ]
}
```

Required item fields: `path`, `prompt`, `type`, `status`, and `summary`. `title` and `typeLabel` are strongly recommended.

## Directory Rules

- Use lowercase route slugs from `references/repertoire.md`.
- End route paths with `/` in the manifest.
- Store each `PROMPT.md` next to the generated `index.html`.
- Use relative links in the root catalog so the directory works locally and on static hosts.
- Keep every route independently hostable. Opening `route/index.html` directly should not require build steps.

## Failure Policy

Benchmark mode prioritizes fairness over perfection:

- No retries by default.
- No sibling-output context in workers.
- No coordinator cleanup inside a generated route except file placement and status recording.
- Failed routes stay in the manifest with `ERROR`, `PARTIAL`, or another clear status.

If the user requests production polish after the benchmark run, create a second curated pass. Mark `mode` as `curated` and describe which routes were repaired.
