---
name: nanobanana-infographic
description: "Creates infographic prompts and renders them with Nano Banana 2.1 (Gemini image API). Use for infographic, executive visual, blog diagram or presentation visual requests, including prompt-only work. Not for logos, memes, raw dashboards, photo edits or general images (use `nanobanana`)."
compatibility: "Python 3 standard library only. GEMINI_API_KEY is needed only for live renders."
---

# Nano Banana 2.1 infographics

Use `gemini-nano-banana-2.1` only; the scripts hard-code it and have no `--model` flag. Older Nano Banana models cost more for worse results or are gone (Nano Banana 2 shut down on 2026-10-29). If a call fails, report it instead of switching models. For photo edits, references, multi-turn refinement or search-grounded images, use `nanobanana`.

## Defaults

- The user's count, channel, ratio, style, palette and content win. A singular request means one image, not a four-render pack. Dark, bold, long-text or multi-panel designs are fine when legible.
- Infer essentials from context; ask only when a missing fact would change the result. Never invent factual claims. Decide the visible copy first, then quote it exactly.
- A prompt-only request needs no API call. A paid render needs the user's authorisation for count, size and passes; a built prompt pack does not authorise renders, and a retry is a new paid call.
- Use `medium` thinking by default, `high` for dense facts, `minimal` only for fact-free layout drafts. State the ratio in the prompt and in the API config, one ratio per pack.
- Never paste the API key anywhere. Saved prompts and responses may hold sensitive content; do not publish them.

## Prompt rules that matter

- "Detailed infographic" produces clutter. Ask for hierarchy, whitespace and a stated number of panels.
- Quote every visible string, ask for it copied character for character, and end with "No other text."; at `medium` and `high` the model adds unrequested captions and labels otherwise.
- One request per intended image; the model may not return the count asked for. Check what came back.
- Dense exact charts, strict brand diagrams and vector-perfect text are better built as vector or chart output than by image generation.
- Output is always JPEG, never transparent (a transparent request draws a checkerboard).
- Brightly coloured palettes are fine; make sure essential distinctions do not rely on colour alone, and give alt text or a text equivalent for accessible publication.

Optional low-noise presets for slides and blogs: `16:9`, near-white base, 2–3 accents, a title of about five words, 1–3-word labels with explanation outside the image. Compositions: Executive Snapshot (one dominant claim plus 3–4 support blocks), Editorial Column (tall stacked panels, thin dividers), Decision Board (modular grid or side-by-side, equal weight), Insight Ribbon (one horizontal band with evenly spaced modules). These are starting points, not limits.

Prompt shape: style, topic, audience, core message, ratio, composition, must-include facts, style details, exact visible text, and the user's real exclusions.

## Checking the render

Open each image and check facts, wording, units, qualifiers, attribution, contrast and ratio against the brief. A successful HTTP call or manifest is not a visual check. Fix factual errors and illegibility; do not rerender endlessly for a subjective target. If exact wording keeps failing, propose a text overlay or a vector workflow. If the render is noisy, simplify grouping and remove callouts before raising the size.

## Scripts

Run each with `--help`.

- `scripts/build_variant_pack.py --brief templates/brief.json --output-dir out/prompt-pack` writes 1–4 preset prompts (four by default, clamped to 1–4). It truncates titles to five words, prescribes 1–3-word labels, forces a white base, and stores `tone` without using it. For dark or bold styles, longer copy or other counts, write prompts yourself. The sample brief's claims are illustrative, not sourced.
- `scripts/render_variant_pack.py --variant-pack <json> --output-dir <dir> --image-size 1K --thinking medium --passes 1 --max-concurrency 2 --dry-run` plans or renders a pack concurrently. Always run `--dry-run` first; drop it only for an authorised batch. It consumes each entry's `id`, `name` and `prompt` from the JSON (editing `.prompt.txt` files changes nothing), needs filesystem-safe unique IDs, and rejects unsupported ratio, size or thinking before any call. For a custom pack write `{"brief": {"aspect_ratio": "4:5"}, "variants": [{"id": "...", "name": "...", "prompt": "..."}]}`.
- `scripts/probe_gemini_image_api.py --prompt-file p.txt --output-dir out --aspect-ratio 4:5 --image-size 1K --thinking medium --passes 1` renders one authorised image. It has no dry-run; keep `--passes 1`.

Read `references/api.md` for request fields, ratios and measured sizes, cost, and error handling.
