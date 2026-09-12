# Nano Banana 2 Infographic

Portable production skill for creating sleek, low-noise Nano Banana 2 infographics for blog posts, executive decks, reports, and editorial explainers.

## What It Covers

- default four-variant infographic prompt packs
- a `16:9` default aspect ratio with clean override rules
- concise question-asking when the brief is underspecified
- verified Nano Banana 2 Gemini API syntax and local probe scripts
- concurrent batch rendering for the full review pack
- clutter, text, and palette controls for executive-grade outputs

## Key Files

- `SKILL.md` for the authoritative instructions
- `references/api.md` for model IDs and request shape
- `references/patterns.md` for the four-variant system and prompt formula
- `references/configuration.md` for local helper scripts
- `references/gotchas.md` for noise and text pitfalls
- `scripts/build_variant_pack.py` to materialize four prompt variants
- `scripts/render_variant_pack.py` to render the whole pack concurrently
- `scripts/probe_gemini_image_api.py` to verify the prompts against Gemini
