---
name: nanobanana-infographic
description: "Create infographic prompts and render workflows with Nano Banana 2, with adaptable low-noise presets for posts, decks, reports, and explainers. Trigger on infographic, Nano Banana 2, Gemini image, executive visual, blog diagram, or presentation visual. Do NOT use for logos, memes, or raw dashboards."
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

Create legible, fact-faithful infographics that fit the user's brief. Low-noise editorial layouts are useful presets, not the only valid style.

This skill uses Nano Banana 2 only. For API calls, use its callable model ID rather than assuming the public marketing name is the exact endpoint name. If the documented ID is uncertain, unavailable, or conflicts with observed behavior, verify current official model documentation and, when authorized, model availability. Do not silently substitute another model.

## Decision Tree

What do you need to do?

- The brief is incomplete or fuzzy
  Infer sensible essentials from the context. Ask only when a missing fact or unresolved choice would materially change the result; do not invent factual claims.

- The user wants an infographic now
  Create the requested number in the requested format and style; an unspecified singular request means one image, not a four-render pack. Use `references/patterns.md` for composition examples when helpful.

- The user wants live Gemini renders or proof that the prompt works
  Read `references/configuration.md`, confirm the authorized scope and spend, then use the single-prompt or batch route that fits.

- The user wants exact API syntax, model IDs, or request fields
  Read `references/api.md`.

- The result looks noisy, text-heavy, or poster-like
  Read `references/gotchas.md` if needed, diagnose the mismatch with the brief, and revise. A bold poster-like style is not itself a defect.

## Default Operating Mode

- Let the requested count, channel, ratio, style, palette, and content control the result. Otherwise choose a coherent composition suited to the audience; explain material assumptions briefly.
- Author a custom prompt directly when the presets do not fit. Dark canvases, bold palettes, gradients, longer text, and other layouts are valid when legible and appropriate.
- Use separate requests for distinct images rather than trusting one request to return an exact image count. Check the actual outputs.
- Render only the authorized images and passes. A prompt-only request needs no API call; a single-image request does not authorize four paid alternatives or open-ended retries.
- Preserve exact facts, units, qualifiers, labels, and required attribution. Decide visible copy before rendering and inspect it afterward; never truncate meaning merely to satisfy a word-count preset.
- Keep credentials secret and send only content authorized for the external service. Saved prompts and responses can contain sensitive material; do not publish them by default.

## Intake Questions

Use these only for material gaps that cannot be resolved from the brief:

| Missing | Ask |
|---|---|
| Topic or claim | "What is the infographic about, in one sentence?" |
| Audience or channel | "Where will this live: blog post, deck, report, keynote, or something else?" |
| Facts or sections | "Which numbers, claims, or sections must appear?" |
| Style boundaries | "Any brand colours, must-avoid looks, or reference tone?" |

If the essentials are supplied or reasonably inferable, proceed without a questionnaire. Missing optional style preferences are not a blocker.

## Quick Reference

| Need | Do | Output |
|---|---|---|
| Custom image | Write a prompt directly; use `scripts/probe_gemini_image_api.py` only for an authorized render | the requested composition without preset constraints |
| Low-noise prompt pack | Run `scripts/build_variant_pack.py` with a brief JSON | 1-4 preset prompts; defaults to four, with a markdown review sheet |
| Approved parallel render | Run `scripts/render_variant_pack.py` on a reviewed pack | all included variants rendered concurrently plus a batch manifest |
| Optional composition examples | Try Executive Snapshot, Editorial Column, Decision Board, or Insight Ribbon | starting points, not an exhaustive design menu |
| Noise reduction | Remove extra panels, colors, and prose before re-rendering | cleaner second pass |

## Optional Low-Noise Presets

For restrained slide or blog visuals, try `16:9`, a white or near-white base, 2-3 accents, a title of roughly five words, and short labels with explanation outside the image. These are starting choices, not universal limits; retain longer required copy, source notes, or paragraphs when the format needs them. The generator implements a stricter preset, including title truncation: see `references/configuration.md` before using it for exact wording or custom styles.

| Variant | Best For | Direction |
|---|---|---|
| Executive Snapshot | C-suite slides, board pre-reads, strategic summaries | one dominant claim or number with 3-4 disciplined support blocks |
| Editorial Column | Blog posts, reports, explainers | tall stacked panels with generous whitespace and thin dividers |
| Decision Board | trade-offs, frameworks, comparisons | modular grid or side-by-side layout with equal visual weight |
| Insight Ribbon | keynote hero slides, opener visuals, and wide summaries | one horizontal narrative band with evenly spaced support modules |

Use `references/patterns.md` for adaptable prompt shapes and targeted iteration.

## Rendering Rules

- State the chosen ratio in both the prompt and API configuration; use a supported format rather than silently overriding the user's target.
- Organize related ideas with clear hierarchy. Combined process, comparison, illustration, or glossary elements can work if their relationships remain understandable.
- Verify text and visual encodings at the intended display size, including contrast and meaning beyond color alone. Supply alt text or a text equivalent when delivering an image for accessible publication.
- Fix factual errors, missing required content, and illegibility before delivery. Plan further paid attempts within the user's scope rather than rerendering automatically until a subjective style target is met.

## Gotchas

1. Asking for a "detailed infographic" usually increases clutter rather than clarity. Ask for hierarchy, whitespace, and restraint instead.
2. Google documents that the model might not create the exact number of images requested. Use one deliberate request per intended image, then inspect the returned count.
3. Google also documents that text generation works best when the text is decided first and then rendered into the image. Do not improvise long copy inside the image prompt.
4. If the image misses the intended tone or scan path, adjust hierarchy, grouping, or emphasis without discarding a requested bold style.
5. When the user needs dense quantitative fidelity, hand-built charts or vector layouts may be a better fit than Gemini image generation.

## Keeping Guidance Useful

Rely on stable principles: factual fidelity, hierarchy, contrast, legibility, and fit to the publishing context. When guidance is insufficient or conflicts with observed behavior, consult current official Gemini/tool documentation or trusted subject sources for the disputed fact; do not browse on every prompt-writing task. Propose a sourced correction to the canonical skill with an example or check, rather than silently changing installed copies. Historical model probes are evidence from that date, not a guarantee of current availability.

## Reading Guide

| Task | Read |
|---|---|
| Model IDs, request fields, aspect ratios, response shape | `references/api.md` |
| Variant design, question flow, prompt formula, iteration ladder | `references/patterns.md` |
| Environment setup, scripts, and live verification commands | `references/configuration.md` |
| Noise, text, language, and retry pitfalls | `references/gotchas.md` |
