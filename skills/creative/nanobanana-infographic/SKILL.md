---
name: nanobanana-infographic
description: "Create sleek, low-noise infographic prompts and render workflows with Nano Banana 2 for posts, decks, reports, and explainers. Trigger on infographic, Nano Banana 2, Gemini image, executive visual, blog diagram, or presentation visual. Do NOT use for logos, memes, or raw dashboards."
compatibility: "Requires: python3. Optional: GEMINI_API_KEY for live render verification."
metadata:
  version: "1.0.0"
  short-description: "Low-noise Nano Banana 2 infographic prompting and verification"
  openclaw:
    category: "content"
    subcategory: "image-generation"
    requires:
      bins: [python3]
      env: [GEMINI_API_KEY]
    cliHelp: "python3 scripts/probe_gemini_image_api.py --help"
    tags: ["gemini", "nano-banana", "infographic", "presentation", "blog"]
references:
  - api
  - patterns
  - configuration
  - gotchas
---

# Nano Banana 2 Infographic

Create sleek, rich, non-noisy infographic prompts and review sets for Gemini image generation.

This skill uses Nano Banana 2 only. For API calls, use the live callable model ID rather than assuming the public marketing name is the exact endpoint name.

## Decision Tree

What do you need to do?

- The brief is incomplete or fuzzy
  Ask only for the missing essentials: topic, audience/context, must-include facts, and brand or style constraints.

- The user wants an infographic now
  Prepare four review variants by default at `16:9` unless the user specified another ratio. Read `references/patterns.md`.

- The user wants live Gemini renders or proof that the prompt works
  Read `references/configuration.md`, then run `scripts/probe_gemini_image_api.py`.

- The user wants exact API syntax, model IDs, or request fields
  Read `references/api.md`.

- The result looks noisy, text-heavy, or poster-like
  Read `references/gotchas.md`, simplify the composition, and regenerate.

## Default Operating Mode

- Offer four distinct variants by default unless the user explicitly asks for fewer.
- Default aspect ratio to `16:9`.
- Use Nano Banana 2 only. Do not fall back to older image models unless the user explicitly asks.
- Render the default pack concurrently when you need live outputs fast.
- Use separate render passes for the variants instead of trusting one request to return the exact number of images requested.
- Keep visible text short: title up to 5 words, labels 1-3 words, no paragraphs in the image.
- Prefer editorial restraint over maximal detail. If a choice would add noise, cut it.

## Intake Questions

Ask these only when they are not already answered:

| Missing | Ask |
|---|---|
| Topic or claim | "What is the infographic about, in one sentence?" |
| Audience or channel | "Where will this live: blog post, deck, report, keynote, or something else?" |
| Facts or sections | "Which numbers, claims, or sections must appear?" |
| Style boundaries | "Any brand colours, must-avoid looks, or reference tone?" |

If the user already gave the essentials, do not re-interview them. Build the variant pack immediately.

## Quick Reference

| Need | Do | Output |
|---|---|---|
| Fast prompt pack | Run `scripts/build_variant_pack.py` with a brief JSON | four prompt variants plus a markdown review sheet |
| Fast parallel render | Run `scripts/render_variant_pack.py` on `variant-pack.json` | all variants rendered concurrently plus a batch manifest |
| Live render proof | Run `scripts/probe_gemini_image_api.py` on one prompt | saved response JSON and local image files |
| Default professional set | Use Executive Snapshot, Editorial Column, Decision Board, and Insight Ribbon | four reviewable directions |
| Noise reduction | Remove extra panels, colors, and prose before re-rendering | cleaner second pass |

## Default Variant Quartet

| Variant | Best For | Direction |
|---|---|---|
| Executive Snapshot | C-suite slides, board pre-reads, strategic summaries | one dominant claim or number with 3-4 disciplined support blocks |
| Editorial Column | Blog posts, reports, explainers | tall stacked panels with generous whitespace and thin dividers |
| Decision Board | trade-offs, frameworks, comparisons | modular grid or side-by-side layout with equal visual weight |
| Insight Ribbon | keynote hero slides, opener visuals, and wide summaries | one horizontal narrative band with evenly spaced support modules |

Read `references/patterns.md` for the exact prompt shape and regeneration ladder.

## Rendering Rules

- Say `16:9` explicitly unless the user asked for another ratio.
- Ask for a white or near-white base, restrained accents, and flat editorial graphics.
- Keep to 2-3 accent colours plus gray or white.
- Use one visual idea per image. Do not combine process, comparison, glossary, and hero illustration in the same render.
- Put the long explanation outside the image. Generate the copy first, then render only the short text that must appear.

## Gotchas

1. Asking for a "detailed infographic" usually increases clutter rather than clarity. Ask for hierarchy, whitespace, and restraint instead.
2. Google documents that the model might not create the exact number of images requested. Treat the four default variants as four deliberate passes.
3. Google also documents that text generation works best when the text is decided first and then rendered into the image. Do not improvise long copy inside the image prompt.
4. If the image looks like a poster, reduce the number of panels, colors, and icon families before changing everything else.
5. When the user needs dense quantitative fidelity, hand-built charts or vector layouts may be a better fit than Gemini image generation.

## Reading Guide

| Task | Read |
|---|---|
| Model IDs, request fields, aspect ratios, response shape | `references/api.md` |
| Variant design, question flow, prompt formula, iteration ladder | `references/patterns.md` |
| Environment setup, scripts, and live verification commands | `references/configuration.md` |
| Noise, text, language, and retry pitfalls | `references/gotchas.md` |
