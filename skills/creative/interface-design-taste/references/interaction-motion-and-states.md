# Interaction, Motion, And States

Motion quality matters, but state design matters first.

## Complete The State Model

Every important component should account for:

- idle
- hover
- focus
- pressed
- selected
- disabled
- loading
- empty
- success
- error

If a component only looks designed when nothing is happening, it is unfinished.

## Motion Tiers

### Tier 0: Still

Use for:

- dense tools
- critical workflows
- contexts where speed and calm matter more than personality

Allowed motion:

- fast hover and focus feedback
- small opacity or transform changes

### Tier 1: Supportive

Use for:

- most product apps
- onboarding
- controlled navigation transitions

Allowed motion:

- staggered entry
- panel and modal transitions
- list reordering feedback

### Tier 2: Expressive

Use for:

- launches
- showcase sections
- storytelling pages

Allowed motion:

- larger scroll choreography
- media reveals
- stronger spatial transitions

Do not carry Tier 2 motion wholesale into repeated working surfaces.

## Interaction Rules

1. Show what changed.
2. Make targets feel pressable before they are pressed.
3. Preserve continuity when objects move between states.
4. Keep timings consistent across a family of actions.
5. Respect keyboard and assistive states, not just pointer hover.

## Forms And Inputs

Good form behavior includes:

- label above field
- helper text when the choice is ambiguous
- inline error where the fix happens
- clear success or completion feedback

Avoid:

- floating labels that compete with typed values
- placeholder-only instructions
- success states that look identical to idle states

## Loading, Empty, And Error States

### Loading

- match the shape of the final layout
- avoid spinner-only waiting when the layout can be hinted

### Empty

- explain what the object is and how to populate it
- include one clear next action

### Error

- say what failed
- say what the user can do next
- keep recovery local when possible

## Dense Product Motion

For dense apps and desktop tools:

- keep transitions short
- animate opacity and transform before more theatrical effects
- avoid motion that causes table or panel content to lose position
- use motion to preserve context when panes, rows, or filters change

## Showcase Motion

For high-expression surfaces:

- concentrate motion in specific narrative sections
- keep supporting sections calmer
- let typography, crop, and pacing do as much work as the animation

## See Also

- `platform-adaptation.md` for motion expectations by platform
- `gotchas.md` for over-animation and incomplete-state mistakes

