# Design Systems And Tokens

Capture the direction only after the product-level decisions are clear. Otherwise you will formalize weak instincts into reusable rules.

## What To Capture

At minimum, define:

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
2. chosen family
3. taste axes
4. visual rules
5. component rules
6. state rules
7. platform-specific adjustments

Use `templates/design-brief-template.md` when you need a repeatable skeleton.

## When To Fork Variants

Fork variants only when the context changes materially:

- marketing vs product
- web vs desktop
- dense operations vs guided onboarding

Do not fork just because one screen wanted more flair.

## See Also

- `platform-adaptation.md` for where the system should diverge
- `interaction-motion-and-states.md` for behavior rules
