# Critique Workflow

When redesigning an existing interface, do not jump straight to colors or hero sections. Audit the work in order of leverage.

## Audit Order

Use this as a starting order; prioritize observed task failures and the user's requested scope over completing every category.

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

- marketing patterns that displace essential tools
- desktop behavior flattened into mobile-style simplicity
- ornamental motion that interrupts tasks or lacks accessible alternatives

## Redesign Sequence

1. Identify what works and what interferes with the user's task or desired expression.
2. Re-establish grouping and dominance.
3. Rewrite labels where they are vague.
4. Clarify color and surface relationships, simplifying where it helps.
5. Complete the missing states.
6. Preserve or develop character, including mixed styles and decorative moments, where it serves the brief.

The two-second glance and removing 20% of chrome can expose hierarchy problems. Neither is a pass/fail threshold or deletion quota; judge comprehension and usefulness for the actual audience.

## Deliverable Format

Scale feedback to the request. A useful review can include:

1. one-paragraph diagnosis
2. ordered findings by severity
3. the highest-leverage fixes, without filling a quota
4. relevant taste-axis shifts, if they clarify the recommendation
5. a proposed direction or combination of styles, if relevant

Use `templates/critique-scorecard.md` when a reusable review format helps.

## See Also

- `principles.md` for the foundational rules
- `gotchas.md` for frequent false moves during redesigns
