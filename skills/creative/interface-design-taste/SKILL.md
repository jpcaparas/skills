---
name: interface-design-taste
description: "Design high-quality product apps, marketing sites, dashboards, and desktop UI. Use for art direction, critique, redesign, hierarchy, layout, typography, color, motion, or lightweight design systems. Do NOT use for logos, illustration-only work, image prompts, or backend-only tasks."
compatibility: "Requires: markdown-reading support. Optional: access to the target repo, screenshots, and local build tooling."
metadata:
  version: "1.0.0"
  short-description: "Product-appropriate interface taste for web, app, and desktop design"
  openclaw:
    category: "design"
    subcategory: "interface-design"
    tags: ["ui", "ux", "web", "desktop", "design-system", "redesign"]
references:
  - principles
  - style-families
  - layout-and-rhythm
  - typography-and-copy
  - color-material-and-iconography
  - interaction-motion-and-states
  - platform-adaptation
  - critique-workflow
  - design-systems-and-tokens
  - gotchas
---

# interface-design-taste

Build interfaces that feel deliberate, product-appropriate, and structurally clear instead of generic, noisy, or under-designed.

## Decision Tree

What kind of design problem are you solving?

- Need a direction from scratch for a site, app, or desktop product
  - Use `references/principles.md` if the brief needs grounding
  - Use `references/style-families.md` if examples would help explore a direction

- Need to improve an existing interface without rewriting everything blindly
  - Read `references/critique-workflow.md`
  - Then branch into the weakest layer: layout, typography, color, motion, or platform fit

- Need stronger hierarchy, composition, spacing, or screen structure
  - Read `references/layout-and-rhythm.md`

- Need better type choices, copy tone, labels, or information cadence
  - Read `references/typography-and-copy.md`

- Need a tighter palette, clearer surfaces, better icons, or more intentional imagery
  - Read `references/color-material-and-iconography.md`

- Need hover/focus/active states, transitions, onboarding flow polish, or motion guidance
  - Read `references/interaction-motion-and-states.md`

- Need platform-specific guidance for marketing web, product web, or desktop UI
  - Read `references/platform-adaptation.md`

- Need to turn the design direction into reusable tokens and component rules
  - Read `references/design-systems-and-tokens.md`
  - Use `templates/design-brief-template.md`

- Need traps, failure modes, or "why does this still feel off?" answers
  - Read `references/gotchas.md`

## Quick Reference

| Need | Read | Outcome |
| --- | --- | --- |
| Turn a vague prompt into a design direction | `references/principles.md` | clear priorities and useful planning dimensions |
| Explore visual approaches without copying a trend | `references/style-families.md` | adaptable examples, including coherent combinations |
| Fix hierarchy and composition | `references/layout-and-rhythm.md` | stronger screen structure and spacing logic |
| Fix type, labels, and tone | `references/typography-and-copy.md` | cleaner hierarchy and more credible copy |
| Fix palette, surfaces, icons, or imagery | `references/color-material-and-iconography.md` | intentional visual relationships and readable contrast |
| Fix motion and all UI states | `references/interaction-motion-and-states.md` | purposeful transitions and complete interaction design |
| Adapt the same idea to site, app, or desktop | `references/platform-adaptation.md` | platform-appropriate behavior and density |
| Audit an existing screen or flow | `references/critique-workflow.md` | prioritized redesign sequence |
| Capture the result as a reusable system | `references/design-systems-and-tokens.md` | tokens, component rules, and handoff structure |

## Default Workflow

1. Identify the artifact, user task, and requested character: marketing page, content page, product surface, dashboard, or desktop tool.
2. Use the taste axes or relevant references when they clarify a decision; skip a worksheet when the brief already supplies direction.
3. Develop a coherent composition. Mixing styles, expressive motion, and one-off flourishes can serve the brief; connect them through hierarchy, rhythm, or another deliberate relationship.
4. Check hierarchy, interaction states, accessibility, and platform fit alongside expression. Preserve the user's intent rather than substituting a house style.
5. Capture reusable tokens and component rules when reuse, handoff, or design-system work calls for them, not for every one-off screen.

## Taste Axes

These optional dimensions can make vague "make it nicer" requests more concrete. Use whichever help; they are neither a required worksheet nor a fixed style menu.

| Axis | Low End | High End | What It Controls |
| --- | --- | --- | --- |
| Composure | restrained | theatrical | how loudly the interface performs |
| Density | spacious | operational | how much work fits into a screen |
| Contrast | soft | sharp | edge definition, hierarchy, and tension |
| Materiality | flat | layered | borders, shadows, blur, and surface depth |
| Motion | still | expressive | movement for feedback, narrative, atmosphere, or delight |

Use the axes as discussion aids, not scores to optimize. A dense desktop tool can still be calm or playful. A marketing page can still be restrained.

## Operating Rules

1. Fit the product before fitting a trend. The right answer for a workflow tool is not the same as the right answer for a launch page.
2. Establish hierarchy at three distances: page structure, section structure, and component structure.
3. Treat states as part of the design, not implementation leftovers. Empty, loading, success, error, hover, focus, and selected states all count.
4. Motion may clarify change or add expression and delight. Keep controls responsive, respect reduced-motion preferences, and avoid flashing or movement that makes content unsafe or hard to use.
5. Use repetition where it helps recognition; allow deliberate exceptions and decoration where they add meaning or character without obscuring tasks.
6. Prefer specific, believable copy and realistic data over placeholder language.
7. Preserve readable contrast, keyboard access, visible focus, and understandable labels across styles. Do not rely on color alone for essential meaning.

## Platform Guardrails

- Marketing web:
  - Allow more dramatic pacing and asymmetry.
  - Let imagery and motion carry more narrative weight.

- Product web:
  - Favor navigational clarity, repeated tasks, and fast scanability.
  - Expressive styling and motion can fit; keep essential feedback recognizable and repeated tasks unblocked.

- Desktop:
  - Design for density, keyboard use, secondary controls, and longer sessions.
  - Adapt promotional gestures so they do not displace working space or precision controls.

Use `references/platform-adaptation.md` when translating a visual language between these contexts.

## Review Questions

Use the questions relevant to the task before finalizing. The two-second glance and 20% removal are diagnostic heuristics, not timing gates or reduction quotas; dense reference tools and expressive experiences may need different checks.

1. What is the first thing the user should notice in under two seconds?
2. What would disappear if you removed 20% of the chrome?
3. Which states are still undesigned?
4. Does the interface feel like the product category, or like a generic AI demo?
5. Would this still hold up with real content, messy data, and long labels?

## Gotchas

1. A beautiful hero does not rescue a weak working surface.
2. Extra shadows do not create hierarchy if the grouping is wrong.
3. Unclear color roles can create competition; a rich palette can work when hierarchy and contrast remain readable.
4. Dense interfaces fail from rhythm problems more often than from lack of whitespace.
5. Desktop tools need affordances for precision, not just prettier cards.
6. Decorative motion cannot substitute for missing interaction feedback, even when theater is part of the brief.
7. A design system created too early can freeze a bad direction into reusable parts.

## Keeping Guidance Useful

Start with stable principles: hierarchy, legibility, task fit, accessible interaction, and coherent expression. If this guidance is insufficient or conflicts with observed behavior, consult current official platform/tool or accessibility documentation, or trusted design research for the specific question; routine design work does not require browsing. Propose a sourced correction to the canonical skill with a concrete example or check. Do not silently mutate installed copies.

## Reading Guide

| If the task is... | Read |
| --- | --- |
| "Give this project a stronger visual direction" | `references/principles.md` for grounding or `references/style-families.md` for examples, as needed |
| "This screen feels flat and generic" | `references/layout-and-rhythm.md` and `references/color-material-and-iconography.md` |
| "The hierarchy is off and the copy feels weak" | `references/typography-and-copy.md` |
| "The interactions are clumsy or unfinished" | `references/interaction-motion-and-states.md` |
| "Make this work as both web and desktop" | `references/platform-adaptation.md` |
| "Audit what exists and tell me what to fix first" | `references/critique-workflow.md` |
| "Turn this into a reusable component system" | `references/design-systems-and-tokens.md` plus `templates/design-brief-template.md` |
| "Why does this still feel cheap?" | `references/gotchas.md` |

## Helper Files

- `references/README.md` — reference index and routing overview
- `templates/design-brief-template.md` — reusable brief for new work
- `templates/critique-scorecard.md` — audit and redesign worksheet
- `scripts/validate.py` — structural validator for this skill
- `scripts/test_skill.py` — packaging and content coverage checks
