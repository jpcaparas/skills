# Gemini Infographic Gotchas

> This file captures the main ways Nano Banana style infographic prompts drift into clutter.

## 1. "Detailed" Often Means "Busy"

If you ask for a "detailed infographic", Gemini often adds more surfaces, icons, arrows, and decorative fragments than the idea can support.

Fix:

- ask for hierarchy, whitespace, and editorial restraint
- specify the number of panels
- keep one story per image

## 2. Too Much Visible Text Breaks Fast

Google's limitations guidance says text-first workflows work best: decide the text first, then generate the image with that text.

Fix:

- keep titles to 5 words or fewer
- keep labels to 1-3 words
- move explanation, evidence, and citations outside the image

## 3. Do Not Trust A Single Request To Yield Three Good Variants

Google also documents that the model might not create the exact number of images you ask for.

Fix:

- run four deliberate render passes
- treat each pass as a named design direction
- compare the saved outputs side by side

## 4. Too Many Colours Create Poster Energy

Bright multi-colour palettes push the result toward "startup poster" or "conference banner" instead of executive communication.

Fix:

- stay with 2-3 accents plus gray or white
- prefer one dark neutral and one main accent
- use colour for hierarchy, not decoration

## 5. Mixed Visual Metaphors Increase Noise

If one image mixes metaphor illustration, process diagram, data labels, and collage textures, it stops scanning cleanly.

Fix:

- pick a single metaphor family
- keep icons from one family only
- remove background flourishes first

## 6. Omitted Aspect Ratio Leads To Unstable Layout

If you do not state the ratio, Gemini may choose a shape that fights the intended editorial layout.

Fix:

- default to `16:9`
- switch to `3:4` when the asset is intentionally tall and article-first
- switch to `4:5` or `9:16` only when the publishing channel demands it

## 7. Language Matters

When legibility matters, English is still the safest default prompt language unless the current Nano Banana 2 docs for your surface say otherwise.

Fix:

- write the prompt in English unless there is a strong reason not to
- keep visible labels even shorter when you must render in another language

## 8. Use A Better Tool When Precision Is The Real Requirement

Some visuals should not be image-generated at all:

- dense KPI dashboards
- exact charts with precise scales
- branded diagrams with strict corporate design systems
- assets that need vector-perfect text placement

In those cases, use a charting or vector workflow instead of forcing Gemini to behave like a layout engine.

## 9. Marketing Names And API IDs Drift

Public launch language and callable API model IDs do not always match exactly.

Observed example:

- Google's February 26, 2026 announcement names the product `Nano Banana 2` and describes it as `Gemini 3.1 Flash Image`.
- A live `ListModels` call on April 9, 2026 exposed the callable Developer API model as `gemini-3.1-flash-image-preview`.

Fix:

- use the public name when talking to users
- use the callable model ID when writing code
- re-check `ListModels` if the naming looks inconsistent again

## 10. Serial Rendering Wastes Time Once The Pack Is Stable

After the prompt pack is written, serially rendering each variant leaves network time idle.

Fix:

- use `scripts/render_variant_pack.py` for the first full review sweep
- use `scripts/probe_gemini_image_api.py` only for one-off rerenders or debugging

## See Also

- `references/patterns.md` for the regeneration ladder
- `references/api.md` for the exact request fields
- `references/configuration.md` for the local scripts
