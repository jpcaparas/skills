# Quality Bar

## Table of Contents

- [Single-File Route Rules](#single-file-route-rules)
- [Minimum Craft](#minimum-craft)
- [Accessibility](#accessibility)
- [Performance](#performance)
- [Validation Checklist](#validation-checklist)

## Single-File Route Rules

Every generated route `index.html` must be a standalone static file:

- Start with `<!DOCTYPE html>` and end with `</html>`.
- Embed route CSS and JavaScript in the file.
- Use no external images.
- Use no framework runtime.
- Use vanilla JavaScript for interaction.
- Use inline SVG, CSS gradients, CSS drawing, canvas, and text as visual material.
- Remote fonts are acceptable when they use `font-display: swap`; the route must still look acceptable if they fail.

## Minimum Craft

Each route needs:

- At least five distinct sections.
- A hero that immediately communicates the theme.
- One canvas, inline SVG, CSS-drawn, or procedural visual system.
- Scroll-triggered reveals using Intersection Observer where practical.
- At least two depth layers or parallax-like spatial moves.
- One marquee, ticker, instrument, map, chart, or unexpected thematic section.
- A footer with fictional but plausible details.

## Accessibility

- Preserve semantic heading order.
- Give interactive controls visible focus states.
- Do not rely on color alone for status or meaning.
- Keep contrast readable over textures and canvas layers.
- Add `prefers-reduced-motion` handling.
- Avoid cursor effects that block touch or keyboard use.

## Performance

- Avoid per-scroll layout thrash. Prefer Intersection Observer and requestAnimationFrame.
- Keep particle counts modest on mobile.
- Pause or simplify expensive animation under reduced motion.
- Use `will-change` only on elements that actually animate.
- Avoid giant embedded data URIs except for small SVG textures.

## Validation Checklist

Before finishing a catalog:

1. Confirm every manifest item has a directory.
2. Confirm every route has `PROMPT.md` and `index.html`.
3. Confirm the root index links to each route and prompt.
4. Confirm every route is single-file static HTML.
5. Confirm no remote image URLs or remote framework scripts are used.
6. Run `scripts/validate_catalog.py` on the generated directory when available.
