# Nano Banana 2 Infographic

Portable production skill for creating legible, fact-faithful Nano Banana 2 infographics for blog posts, executive decks, reports, and editorial explainers. The authoritative instructions live in `SKILL.md`.

## What It Covers

- user-led format, style, content, and image count, including bold or dark designs
- optional low-noise composition presets and a four-prompt preset builder
- direct custom prompts when the builder's fixed style or text limits do not fit
- material-gap questions rather than an intake questionnaire
- Gemini request examples, dated model evidence, and conditional official-doc checks
- single-image or approved concurrent batch rendering, with factual, accessibility, privacy, and spend checks

## Key Files

- `SKILL.md` for the authoritative instructions
- `references/api.md` for model IDs and request shape
- `references/patterns.md` for custom prompts and optional composition examples
- `references/configuration.md` for supported overrides, preset limitations, and local helper scripts
- `references/gotchas.md` for noise and text pitfalls
- `scripts/build_variant_pack.py` to materialize 1-4 preset prompts (four by default; not a render authorization)
- `scripts/render_variant_pack.py` to plan a pack offline with `--dry-run` or render an authorized pack concurrently
- `scripts/probe_gemini_image_api.py` to render a custom or preset prompt when authorized
