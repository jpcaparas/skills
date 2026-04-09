# Prompt Patterns For Sleek Infographics

## Table of Contents

- [When To Ask Questions](#when-to-ask-questions)
- [Three-Variant Default](#three-variant-default)
- [Prompt Formula](#prompt-formula)
- [Quality Gates](#quality-gates)
- [Iteration Ladder](#iteration-ladder)

## When To Ask Questions

Ask follow-up questions only when one of these is missing:

- the subject or core claim
- the audience or placement context
- the must-include numbers, labels, or sections
- the visual boundaries or must-avoid look

Do not ask process questions that the skill can answer itself. If the user asks for "an infographic for a blog post about X", default to:

- three variants
- `16:9`
- white or near-white background
- flat editorial graphics
- restrained palette

## Three-Variant Default

Unless the user says otherwise, produce these three directions:

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
- no decorative background elements

## Prompt Formula

Use this shape. Keep it specific but not overloaded:

```text
Create a sleek editorial infographic, not a busy poster.

Topic: <topic>
Audience/context: <audience>
Core message: <message>
Aspect ratio: <ratio>
Variant direction: <one of the three default variants>

Must include:
- <exact fact or section>
- <exact fact or section>

Composition:
- <layout instructions>
- <hierarchy instructions>
- <icon policy>

Style:
- white or near-white background
- flat 2D editorial graphics
- restrained palette, 2-3 accent colours plus gray/white
- generous whitespace
- clean alignment and spacing

Text rules:
- title max 5 words
- labels 1-3 words
- no sentences, captions, legends, or source notes in the image

Avoid:
- busy collage layouts
- gradients, glow, glassmorphism, bevels, drop shadows
- decorative filler icons
- poster energy
- dashboard clutter
```

## Quality Gates

Reject and rerender when any of these happen:

- the image needs more than a few seconds to parse
- the composition tries to explain two unrelated ideas at once
- there are more than 4-5 meaningful blocks on a single review image
- labels become sentence-like
- the style becomes loud, glossy, or promotional

## Iteration Ladder

When the first pass is wrong, do not rewrite everything immediately.

1. If the image is noisy, cut the number of panels or callouts by 30-50%.
2. If the text is warped, shorten the title and labels before touching layout.
3. If the result feels generic, sharpen the hierarchy, not the decoration.
4. If the image feels empty, add one stronger framing device, not more fragments.
5. If the model keeps missing exact wording, render fewer words or move the longer explanation outside the image entirely.

Use `scripts/build_variant_pack.py` to materialize the default trio from a structured brief.

## See Also

- `references/api.md` for request syntax
- `references/configuration.md` for the helper scripts
- `references/gotchas.md` for model-specific pitfalls
