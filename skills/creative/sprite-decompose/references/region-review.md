# Region specification and visual review

Read this before extraction. Use it to convert native image inspection into an explicit, reviewable region plan and to tune only the settings supported by visual evidence.

## Region fields

The root `schema_version` is `1`.

| Field | Contract |
|---|---|
| `background.model` | `quadratic` for gentle spatial variation; `flat` for one stable color |
| `background.sample_stride` | Pixel interval for fitting; smaller is slower and denser |
| `background.selection_distance` | RGB distance used to retain likely background fit samples |
| `background.fit_iterations` | Bounded robust refits after the dominant-color seed |
| `background_samples` | Optional clear-background rectangles; spread them across the image |
| `matting.core_distance` | RGB distance at or above which pixels are definitely foreground |
| `matting.edge_distance` | Lower RGB distance for feathered edge candidates |
| `matting.edge_growth` | Maximum one-pixel dilation steps from retained core pixels |
| `matting.min_component_area` | Default minimum core-component area in pixels |
| `regions[].bounds` | Source-space `x`, `y`, `width`, and `height` |
| `regions[].name` | Optional unique lowercase slug; omit for `sprite-NNN.png` |
| `regions[].grouping` | Required explanation of what the region keeps together |
| `regions[].component_policy` | `all` retains eligible detached components; `largest` keeps only the largest |
| `regions[].min_component_area` | Optional local override for tiny effects |
| `regions[].fill_holes` | Optional repair for pale enclosed detail; default `false` because true holes may show background |
| `regions[].warnings` | Known review notes copied into the manifest |

Unknown fields fail parsing. Bounds must remain inside the source. Names must match `^[a-z0-9]+(?:-[a-z0-9]+)*$` and remain unique.

## Manual review loop

1. View the source at original resolution and note its exact pixel dimensions.
2. Traverse in a stable reading order, usually top-to-bottom and left-to-right.
3. Draw one region around each logical output, leaving enough background to observe the full fringe without including a neighbor.
4. Decide whether touching artwork belongs together. Record that decision in `grouping`, not only in a filename.
5. Assign detached particles, notes, sparkles, dust, or droplets to a region explicitly. Choose `all` and lower only that region's minimum area when necessary.
6. Extract to a new output directory and inspect every file over both light and dark backgrounds.
7. Compare `visible_source_bounds` with `source_bounds`. Treat any boundary-touch warning as a possible clipped sprite.
8. Tune one cause at a time, rerun, and verify again.

## Tuning by symptom

| Symptom | First review action |
|---|---|
| Pale edge or glow disappears | Lower `core_distance` slightly, then review noise |
| Background halo remains | Raise `edge_distance` or reduce `edge_growth`; if the fringe is fully opaque, raise `core_distance` |
| Tiny assigned effect disappears | Set that region's `min_component_area` to `1` or `2` and keep `all` |
| Neighbor fragment appears | Tighten bounds or use `largest` only when detached detail is not intended |
| Interior pale detail becomes transparent | Consider `fill_holes: true`, then verify genuine holes were not filled |
| Fit follows foreground colors | Add several clear `background_samples` across the source |
| Fit reports deficient rank | Spread samples across both axes or select the `flat` model |

Do not hide a visual tradeoff by changing several thresholds together. Preserve the reviewed JSON beside the outputs when reproducibility matters.
