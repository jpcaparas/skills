# Still Visual Dissection

Use this reference for screenshots, image sets, mockups, posters, illustrations, diagrams, and vectors. Analyse supplied visuals with the active model’s native image capability; do not send them to a third-party vision-analysis service.

## Inspect the Frame

Record what is actually visible:

- canvas or viewport aspect ratio, crop, safe areas, and orientation
- dominant regions, reading order, focal path, balance, and negative space
- container edges, alignment anchors, column relationships, overlap, and depth
- relative proportions before exact dimensions
- type roles, apparent family class, weight, scale, case, line length, and rhythm
- palette roles, contrast, gradients, transparency, texture, light, and shadow
- imagery, iconography, illustration language, masking, and media crops
- repeated components, variants, selected states, badges, controls, and decorative motifs
- exact legible copy, punctuation, numbers, proper nouns, and Unicode

Use extraction or source files for exact colors, typefaces, and dimensions when available. Otherwise use calibrated descriptions or approximate ranges; do not manufacture pixel-perfect values from a resized preview.

## Bound the Missing Evidence

A still image does not prove:

- hover, focus, keyboard, drag, scroll, dismissal, or animation behavior
- what exists outside the crop
- breakpoint behavior beyond the supplied viewports
- loading, empty, error, disabled, or success states not shown
- data persistence, permissions, validation, or navigation
- sound, timing, or reduced-motion behavior

When one image is the only evidence, turn these into explicit reconstruction decisions. Require the future session to create behavior consistent with the visible design, but never call that behavior source-faithful observation.

For image sets:

1. Identify invariants across frames.
2. Treat differences as possible viewport changes, states, or content variants.
3. Use filenames, dimensions, and repeated anchors to infer the strongest correspondence.
4. Keep unresolved conflicts visible when the set does not establish sequence or precedence.

## Prompt Translation

Describe spatial relationships in an order a builder can reconstruct:

1. overall canvas and focal hierarchy
2. major regions and their relative geometry
3. typography and color roles
4. component anatomy and repetitions
5. imagery, surfaces, depth, and decorative identity
6. visible state
7. unobserved behaviors the target still needs, clearly labelled as coherent additions

Require visual comparison against the original at the supplied aspect ratios. If the target is a website or app, require responsive and interactive completeness while preserving the fact that those states were not directly visible.

**Complete when:** the prompt can reproduce the visible composition without false precision and separates every required invention from visual evidence.
