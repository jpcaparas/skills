# Design Systems And Tokens

Use this reference for reuse, handoff, or system work; a one-off design need not produce tokens. Capture the direction after the product-level decisions are clear, and reuse an existing system where appropriate.

## What To Capture

Capture the categories that need shared rules:

1. type roles
2. spacing rhythm
3. radius rules
4. border and divider behavior
5. surface hierarchy
6. accent usage
7. motion tiers
8. state treatments
9. component-family rules

## Token Categories

### Typography

- display
- section title
- body
- label
- meta
- mono numeric

### Spacing

- compact
- standard
- generous
- section

### Surfaces

- base canvas
- raised surface
- embedded surface
- overlay surface

### Feedback

- focus
- success
- warning
- error

## Component Family Rules

Document components by behavior, not just by appearance:

- buttons:
  - hierarchy, hover, active, disabled
- fields:
  - label, hint, error, success
- cards or panels:
  - when to use them and when not to
- tables or lists:
  - row density, hover, selection, empty states
- navigation:
  - primary, secondary, contextual

## Handoff Pattern

Write the design system seed in this order:

1. product context
2. visual direction, including any intentional combination of styles
3. useful taste dimensions, if any
4. visual rules
5. component rules
6. state rules
7. platform-specific adjustments

Use `templates/design-brief-template.md` when you need a repeatable skeleton.

## When To Fork Variants

Shared variants are useful when contexts recur, for example:

- marketing vs product
- web vs desktop
- dense operations vs guided onboarding

A one-off flourish can remain local rather than becoming a system-wide variant. Promote it when reuse makes that worthwhile.

## See Also

- `platform-adaptation.md` for where the system should diverge
- `interaction-motion-and-states.md` for behavior rules
