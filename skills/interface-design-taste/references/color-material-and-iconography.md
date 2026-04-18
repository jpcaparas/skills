# Color, Material, And Iconography

Most weak interfaces use too many visual signals at once. Tight systems feel richer because each signal means something.

## Palette Structure

Build the palette in this order:

1. background or canvas neutrals
2. surface neutrals
3. text neutrals
4. one primary accent
5. semantic status colors

Only add a secondary accent if it has a stable job.

## Accent Budget

Use the primary accent for:

- main actions
- focus states
- active selection
- one or two reinforcing highlights

Do not spend the same accent on:

- decorative gradients
- unrelated tags
- empty-state illustrations
- every chart series by default

## Surface Logic

Choose materiality intentionally:

- low materiality:
  - more lines, dividers, and crisp edges
  - good for tools and dense product views
- medium materiality:
  - selective card use and modest depth
  - good for broad product UI and premium apps
- high materiality:
  - soft layering, blur, or richer surface separation
  - best when the product benefits from warmth or theater

If every object floats, nothing feels important.

## Borders And Shadows

Use borders when you need:

- precision
- grid clarity
- dense grouping

Use shadows when you need:

- elevation
- separation over complex backgrounds
- draggable or layered object behavior

Avoid using both heavy borders and heavy shadows on everything.

## Iconography

Keep icon language consistent:

- similar stroke weight or fill strategy
- similar corner logic
- similar level of detail

Icons should support labels, not replace them on first exposure.

Good icon usage:

- navigation
- compact metadata
- status reinforcement
- object type hints

Weak icon usage:

- decorative clutter
- mixed icon families
- overloaded metaphor icons with no text

## Imagery

Imagery should reinforce the product story, not rescue an empty layout.

- editorial products:
  - quieter image treatment, stronger crop discipline
- product launches:
  - one dominant image idea per section
- product apps:
  - prefer real product views, diagrams, or focused illustrations over generic lifestyle stock

## Charts And Visual Data

Use color conservatively:

- neutral baseline series
- accent on the key series
- semantic colors only for status or threshold meaning

If the screen already has multiple accents, charts should get quieter, not louder.

## Quick Fixes

If the UI feels noisy:

1. reduce accent count
2. simplify shadow behavior
3. standardize border strength
4. unify icon family
5. remove decorative badges that are only using color to ask for attention

## See Also

- `style-families.md` for family-specific palette behavior
- `gotchas.md` for common color and surface mistakes

