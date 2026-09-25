# Gemini Infographic Gotchas

> Diagnose failures against the brief, not against a mandatory minimalist style. These remedies are options; factual fidelity, accessibility, privacy, and authorized spend remain requirements.

## 1. "Detailed" Often Means "Busy"

If you ask for a "detailed infographic", Gemini often adds more surfaces, icons, arrows, and decorative fragments than the idea can support.

Fix:

- ask for hierarchy, whitespace, and editorial restraint
- specify the number of panels
- keep one story per image

## 2. Too Much Visible Text Breaks Fast

Google's limitations guidance says text-first workflows work best: decide the text first, then generate the image with that text.

Fix:

- decide exact visible copy before rendering
- try short titles and labels when the format permits; never truncate required wording or qualifiers
- enlarge text, adjust grouping, or use a text-overlay workflow when longer explanation or citations must stay in the image

## 3. A Request Does Not Guarantee An Exact Image Count

Google also documents that the model might not create the exact number of images you ask for.

Fix:

- use one request per intended image within the authorized count
- check the actual saved outputs, including missing images
- compare variants only when a review set was requested; one image does not need four paid attempts

## 4. Color Needs Readable Relationships

Bright multi-colour palettes can suit promotional or educational work. They become a problem when essential distinctions or text are hard to read, or when the tone conflicts with the brief.

Fix:

- try 2-3 accents plus neutrals as a low-noise preset, not a limit
- keep the requested dark or colorful background when it works
- use labels and other non-color cues for essential meaning; decoration can coexist with hierarchy

## 5. Mixed Visual Metaphors Increase Noise

Mixed metaphors, process diagrams, data labels, and collage textures can compete when their relationships are unclear.

Fix:

- connect the elements through a clear reading order, framing, or shared visual language
- simplify or unify icons if they confuse meaning
- retain requested flourishes when they support character without obscuring content

## 6. Omitted Aspect Ratio Leads To Unstable Layout

If you do not state the ratio, Gemini may choose a shape that fights the intended editorial layout.

Fix:

- choose a ratio for the intended channel and composition; `16:9` is a slide preset, not a universal default
- use tall, square, or panoramic formats when the brief benefits from them
- keep prompt and API ratio consistent, checking official support when uncertain

## 7. Language Matters

Language support and text fidelity can vary by model and delivery surface. Do not replace the requested language with English or shorten meaning on an unsupported assumption.

Fix:

- specify the exact requested language and visible text
- inspect glyphs, spelling, and reading order; consult current official guidance if behavior conflicts with expectations

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
- check official model documentation and, when authorized, `ListModels` if the naming or availability is uncertain; a similar-looking model name is not proof of identity
- report unavailability rather than silently substituting another model

## 10. Parallelism Does Not Authorize Extra Renders

An approved multi-image pack can benefit from concurrent rendering. The preset builder's four prompts do not themselves authorize four API calls.

Fix:

- use the batch script's `--dry-run` to inspect job count and `--max-concurrency` to bound concurrency
- use `scripts/probe_gemini_image_api.py` with a custom prompt for a single image
- inspect failures before further paid attempts; keep retries within the user's budget and protect saved prompts and responses

## See Also

- `references/patterns.md` for the regeneration ladder
- `references/api.md` for the exact request fields
- `references/configuration.md` for the local scripts
