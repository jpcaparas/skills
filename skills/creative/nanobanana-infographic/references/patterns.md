# Prompt Patterns For Infographics

## Table of Contents

- [When To Ask Questions](#when-to-ask-questions)
- [Optional Composition Presets](#optional-composition-presets)
- [Prompt Formula](#prompt-formula)
- [Parallel Rendering](#parallel-rendering)
- [Quality Gates](#quality-gates)
- [Iteration Ladder](#iteration-ladder)

## When To Ask Questions

Resolve these from the brief where possible; ask only when an unknown would materially change the result:

- the subject or core claim
- the audience or placement context
- the must-include numbers, labels, or sections
- the visual boundaries or must-avoid look

Do not ask process questions that the skill can answer itself. For "an infographic for a blog post about X", make one suitable composition. A restrained editorial option might use:

- `16:9`
- white or near-white background
- flat editorial graphics
- restrained palette

Choose another ratio, palette, or composition when the brief or channel calls for it. Missing brand preferences do not require an interview, and a single-image request does not authorize a paid comparison pack.

## Optional Composition Presets

Use, combine, or skip these examples. They are neither an exhaustive menu nor a requirement to produce four variants.

### 1. Executive Snapshot

Use for board decks, investor updates, briefings, and strategic summaries.

Structure:

- one dominant hero claim, number, or framing sentence
- 3-4 supporting modules
- crisp top-down reading order
- higher whitespace than the other variants

### 2. Editorial Column

Use for blog posts, explainers, research reports, and long-form writing.

Structure:

- stacked vertical panels
- thin dividers or subtle section breaks
- one idea per panel
- steady reading rhythm down the page

### 3. Decision Board

Use for comparisons, frameworks, trade-offs, and category maps.

Structure:

- modular grid or side-by-side layout
- equal panel weight
- short comparison labels
- a quiet background when it helps comparison

### 4. Insight Ribbon

Use for hero slides, opener visuals, summary banners, and wide editorial headers.

Structure:

- one horizontal narrative band
- 4 evenly spaced support modules or beats
- strong left-to-right scan path
- minimal vertical stacking

## Prompt Formula

Adapt this shape to the requested style and content:

```text
Create an infographic in <requested or chosen style>.

Topic: <topic>
Audience/context: <audience>
Core message: <message>
Aspect ratio: <ratio>
Composition: <preset, combination, or custom direction>

Must include:
- <exact fact or section>
- <exact fact or section>

Composition:
- <layout instructions>
- <hierarchy instructions>
- <icon policy>

Style:
- <background, palette, material, and imagery suited to the brief>
- <intentional grouping, alignment, and spacing>
- readable text and distinguishable data encodings at the final display size

Exact visible text:
- <title, labels, required explanation, units, and attribution>
- preserve supplied facts and qualifiers without inventing claims

Avoid:
- <actual user exclusions or identified sources of confusion>
```

A title around five words, labels of 1-3 words, and explanation outside the image can help a small slide. They are not limits for all formats. Dark palettes, glow, gradients, decorative illustrations, paragraphs, and multi-part compositions are valid when they fit the brief and remain legible. Do not remove a required source note or qualification just to shorten text.

## Parallel Rendering

For an authorized multi-image pack, inspect a no-spend plan first:

```bash
python3 scripts/render_variant_pack.py \
  --variant-pack ./out/prompt-pack/variant-pack.json \
  --output-dir ./out/renders/batch \
  --dry-run
```

For a live batch, omit `--dry-run` only within the authorized count and budget. Bound concurrency with `--max-concurrency` when needed for quotas. Use `scripts/probe_gemini_image_api.py` with a custom prompt file and `--passes 1` for a single image; it has no dry-run flag.

## Quality Gates

Before delivery, check:

- exact facts, wording, quantities, units, qualifiers, and required attribution
- readable text and contrast at intended size
- clear relationships and an appropriate reading order for the audience
- requested style, ratio, and image count
- an accessible text equivalent and non-color cues for essential distinctions

Glance speed, block count, and text length are diagnostic cues, not automatic rejection rules. A six-panel dark explainer or a glossy promotional infographic may be exactly right. Report unresolved defects; revise or rerender only within the approved scope.

## Iteration Ladder

When the first pass is wrong, do not rewrite everything immediately.

1. If the image is noisy, clarify grouping and emphasis; remove nonessential callouts where useful, without a removal quota.
2. If the text is warped, check size and spacing, then shorten only wording that may change. Preserve exact required copy.
3. If the result feels generic, strengthen hierarchy or introduce a distinctive visual device consistent with the brief.
4. If the image feels empty, adjust scale, framing, or supporting detail rather than filling space automatically.
5. If exact wording keeps failing, propose a text-overlay or vector workflow, or moving explanation outside the image when the brief permits it. Do not spend indefinitely trying to force fidelity.

Use `scripts/build_variant_pack.py` only when its strict low-noise preset fits. It defaults to four prompts and cannot express every choice above; `references/configuration.md` documents its limits and the custom-prompt route.

## See Also

- `references/api.md` for request syntax
- `references/configuration.md` for the helper scripts
- `references/gotchas.md` for model-specific pitfalls
