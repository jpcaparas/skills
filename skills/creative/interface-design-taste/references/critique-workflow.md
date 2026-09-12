# Critique Workflow

When redesigning an existing interface, do not jump straight to colors or hero sections. Audit the work in order of leverage.

## Audit Order

1. product fit
2. information hierarchy
3. layout and grouping
4. typography and labeling
5. color and surfaces
6. interaction states
7. motion
8. polish

If the first three layers are weak, visual polish mostly hides the problem instead of fixing it.

## What To Capture

For each screen or flow, record:

- the user's goal
- the dominant object or action
- the first thing the interface currently emphasizes
- the main source of friction
- the missing or weak states
- the platform mismatch, if any

## Severity Scale

- **Blocker**
  - prevents understanding or task completion
- **High**
  - creates repeated friction, weak trust, or wrong emphasis
- **Medium**
  - reduces clarity or quality but does not break the task
- **Low**
  - polish issue or missed opportunity

## Common Audit Categories

### Hierarchy

- primary action unclear
- too many competing hotspots
- labels weaker than decorative elements

### Layout

- unhelpful card repetition
- no dominant zone
- uneven spacing rhythm
- dense areas and empty voids with no logic

### Typography

- too many sizes
- vague labels
- supporting text louder than primary content

### Color And Surfaces

- accents used everywhere
- surfaces all floating at once
- semantic colors competing with brand colors

### Interaction

- weak hover or focus behavior
- missing empty or error states
- action feedback too subtle or too dramatic

### Platform Fit

- marketing patterns inside tools
- desktop behavior flattened into mobile-style simplicity
- web product screens carrying too much ornamental motion

## Redesign Sequence

1. Remove noise.
2. Re-establish grouping and dominance.
3. Rewrite labels where they are vague.
4. Simplify color and surface logic.
5. Complete the missing states.
6. Reintroduce character only where it supports the thesis.

## Deliverable Format

When giving redesign feedback, produce:

1. one-paragraph diagnosis
2. ordered findings by severity
3. the top three fixes with the highest leverage
4. the taste-axis shift you recommend
5. the target family, if relevant

Use `templates/critique-scorecard.md` when a reusable review format helps.

## See Also

- `principles.md` for the foundational rules
- `gotchas.md` for frequent false moves during redesigns
