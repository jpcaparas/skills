---
name: sprite-decompose
description: "Decompose sprite sheets, sprite atlases, and illustration contact sheets on flat or gently varying backgrounds into one tightly cropped transparent PNG per reviewed logical sprite, plus a bounds/grouping manifest and validation evidence. Use for separating existing multi-asset images; not for generating new sprites, packing an atlas, or reconstructing hidden pixels."
compatibility: "Requires Python 3.11+, Pillow, and NumPy. Native image inspection is required for region and grouping decisions."
metadata:
  version: "1.0.0"
  short-description: "Extract reviewed sprites into transparent PNGs"
references:
  - region-review
---

# Sprite Decompose

Turn a many-illustration raster into transparent, tightly trimmed sprite PNGs while keeping semantic grouping under deliberate visual review.

## Ownership Boundary

Use this skill when the input already contains multiple logical illustrations that must become separate files. Use a generation workflow to create new artwork, a background-removal workflow for one standalone image, or an atlas-packing workflow to combine existing files.

The workflow separates judgment from deterministic work:

- Codex's own image analysis chooses logical regions, names, and grouping decisions.
- `scripts/sprite_decompose.py` fits the background, creates alpha, cleans components, trims exact transparent edges, writes the PNGs and manifest, then verifies them.

Do not use third-party vision analysis services. Local Pillow and NumPy processing is the deterministic implementation, not a semantic detector.

## Workflow

### 1. Inspect and classify the source

Open the full-resolution source with native image viewing. Confirm that the background is flat or changes gently enough to model as a flat or quadratic RGB surface. Identify shadows, glows, particles, pale details, touching objects, and any illustration that reaches a cell edge.

Stop or narrow the claim when the source needs hidden-pixel reconstruction: overlapping or occluded sprites cannot be recovered from a flattened raster.

**Complete when:** every visible asset area has been inspected and every ambiguity that could change grouping or tolerance is recorded.

### 2. Write and review explicit regions

Copy `templates/regions.example.json` and edit it against the source dimensions. Read `references/region-review.md` now; use it to choose bounds, component policy, names, warnings, and threshold adjustments.

Keep touching elements together when they form one logical asset. Split them only when the user wants separate outputs and each requested crop contains the visible pixels it needs. Include detached particles in the intended region and use a per-region `min_component_area` when tiny effects would otherwise be removed.

Supply a lowercase slug in `name` for a meaningful filename such as `kiwi-pair.png`. Omit `name` for stable list-order names such as `sprite-007.png`. Write a concrete `grouping` decision for every region.

**Complete when:** the JSON parses conceptually, region order is intentional, all bounds lie inside the image, names are unique, and every logical sprite has one reviewed grouping decision.

### 3. Install the local raster dependencies

Use a project or disposable virtual environment. From the installed skill directory:

```bash
python3 -m venv .venv
```

Activate it with `source .venv/bin/activate` on macOS/Linux or `.venv\Scripts\Activate.ps1` in PowerShell, then install:

```bash
python -m pip install -r requirements.txt
```

**Complete when:** `python -c "import PIL, numpy"` exits successfully in the selected environment.

### 4. Extract into a new directory

Resolve `<skill-dir>` to this installed skill and run:

```bash
python <skill-dir>/scripts/sprite_decompose.py extract \
  <source-image> <regions.json> <output-directory>
```

The command refuses any existing output path. For a reviewed rerun that intentionally replaces only that output directory, add `--overwrite`. Extraction uses a sibling staging directory, validates the complete staged result, confirms the input image hash is unchanged, and only then publishes the directory.

**Complete when:** the command reports the expected sprite count and the output contains only the declared PNGs plus `manifest.json`.

### 5. Review pixels and grouping

Inspect every PNG at full resolution and against a contrasting checkerboard or solid background. Look for halos, missing pale pixels, clipped shadows, stray neighbor fragments, lost particles, accidental merging, and an output count that disagrees with the reviewed region list.

Adjust the region JSON or matting settings deliberately, then rerun. `perfectly cropped` means no fully transparent border remains after background removal; it does not mean semantic reconstruction.

**Complete when:** every output's visible content, filename, grouping, and warning state agrees with the source and the user's intent.

### 6. Verify the published result

Run the independent verifier:

```bash
python <skill-dir>/scripts/sprite_decompose.py verify <output-directory>
```

The verifier checks manifest ordering and inventory, RGBA PNG mode, dimensions, SHA-256 hashes, visible pixels, and non-empty alpha on all four crop edges. Report warnings and review decisions alongside the successful command; do not turn a structural pass into a claim that visual judgment was automatic.

**Complete when:** verification passes and the handoff names the output directory, sprite count, warnings reviewed, and any limitation that remains visible in the source.

## Output Contract

Each successful output directory contains:

```text
<output-directory>/
├── <meaningful-name>.png or sprite-<NNN>.png
├── ...
└── manifest.json
```

The manifest records source identity and dimensions, resolved settings, background-fit diagnostics, stable order, source and visible bounds, output size, grouping decision, component counts, warnings, and each PNG's SHA-256.

## Limits That Require Review

- Overlap and occlusion leave no evidence for hidden pixels; extraction cannot recreate them.
- Touching elements remain one logical sprite unless the region plan deliberately separates their visible pixels.
- Shadows, glows, particles, and near-background colors need deliberate bounds and tolerance review.
- `component_policy: "largest"` can remove intentional detached detail; use it only when smaller components are known contamination.
- A region boundary warning means visible alpha reached the reviewed box edge. Enlarge the region or accept the warning with evidence.

## Gotchas

1. A dominant-color fit can fail when the background is not the largest coherent color family. Add clear `background_samples` distributed across the image.
2. A quadratic fit needs samples spread in both axes. Use `model: "flat"` for a truly flat background or add spatially distributed samples.
3. Higher `core_distance` removes colors close to the background; lower values retain more pale detail and more background noise.
4. Higher `edge_growth` reaches farther into soft fringes but cannot add a disconnected effect whose core component was discarded.
5. Region order is part of the filename and manifest contract for unnamed sprites. Reordering regions intentionally renumbers those outputs.
