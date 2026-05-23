# UI Guidance

## Table of Contents

- [Variant Brief Shape](#variant-brief-shape)
- [Style-Specific Variation](#style-specific-variation)
- [Catalog UI](#catalog-ui)
- [Responsive Requirements](#responsive-requirements)
- [Common Weak Outputs](#common-weak-outputs)

## Variant Brief Shape

For every route, define the visual system before writing HTML. The brief should cover:

- Layout: hero composition, section order, density, and asymmetric vs grid behavior.
- Typography: display face character, body face, scale contrast, weight strategy, and tracking.
- Color: three to four tones, role of each tone, and which accent is allowed to dominate.
- Spacing: compact, ceremonial, editorial, instrument-like, or airy rhythm.
- Surfaces: open page, bordered panels, translucent layers, hard dividers, or material textures.
- Shape: square, slightly rounded, circular, pill, faceted, or engineered geometry.
- Motion: scroll reveal, canvas atmosphere, SVG stroke draw, ticker, parallax, or stateful UI moment.
- Personality: brand mood and what the page should not feel like.

This upfront definition keeps variants genuinely different instead of producing one layout with swapped colors.

## Style-Specific Variation

Use the style cards in `references/repertoire.md` as constraints, not scripts. Each generated route should make a few fresh choices inside the style:

- Change the brand name and content architecture.
- Pick one signature visual device and execute it well.
- Make the hero reveal the subject immediately.
- Use one unexpected section that fits the theme.
- Keep copy specific enough to feel like a real institution, venue, studio, or product.

## Catalog UI

The catalog page is not one of the showcase routes. Keep it quiet and operational:

- Prioritize scan speed over spectacle.
- Expose path, prompt, type, status, and summary without hover-only details.
- Use a single accent for status or links.
- Keep status labels short and stable.
- Make mobile rows self-labeling so columns are not lost.

## Responsive Requirements

Every route and the root index must work at phone and desktop widths:

- Avoid fixed-width containers that overflow.
- Use fluid grids and clamp-like constraints where appropriate.
- Keep body copy readable on mobile.
- Ensure canvas and decorative layers do not cover controls or text.
- Respect `prefers-reduced-motion` with reduced or disabled animation.

## Common Weak Outputs

- Hero text is large, but the site has no specific subject signal.
- The route has five sections, but every section is the same card grid.
- Motion exists, but it is only decorative and not tied to the theme.
- The palette uses too many accents or collapses into one muddy hue.
- The prompt says "luxury" but the implementation uses generic SaaS spacing and buttons.
- The catalog hides `PROMPT.md` behind unclear labels.
