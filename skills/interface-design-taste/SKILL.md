---
name: interface-design-taste
description: "Design high-quality digital interfaces across product apps, marketing sites, dashboards, and desktop software. Use when a user wants art direction, UI critique, redesign strategy, layout, typography, color, motion, or a lightweight design system that avoids generic defaults while fitting the product. Triggers on: design taste, redesign this UI, improve hierarchy, polish this app, dashboard UI, desktop UI, landing page direction, spacing, type scale, visual language. Do NOT trigger for logo design, illustration-only work, photoreal image prompting, or backend-only tasks with no interface decisions."
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
  - Read `references/principles.md`
  - Then read `references/style-families.md`

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
| Turn a vague prompt into a design thesis | `references/principles.md` | clear priorities, taste axes, and guardrails |
| Choose a visual lane without copying a trend | `references/style-families.md` | one coherent family and what to avoid |
| Fix hierarchy and composition | `references/layout-and-rhythm.md` | stronger screen structure and spacing logic |
| Fix type, labels, and tone | `references/typography-and-copy.md` | cleaner hierarchy and more credible copy |
| Fix palette, surfaces, icons, or imagery | `references/color-material-and-iconography.md` | a restrained visual system with better contrast |
| Fix motion and all UI states | `references/interaction-motion-and-states.md` | purposeful transitions and complete interaction design |
| Adapt the same idea to site, app, or desktop | `references/platform-adaptation.md` | platform-appropriate behavior and density |
| Audit an existing screen or flow | `references/critique-workflow.md` | prioritized redesign sequence |
| Capture the result as a reusable system | `references/design-systems-and-tokens.md` | tokens, component rules, and handoff structure |

## Default Workflow

1. Identify the artifact first: marketing page, content page, product surface, dashboard, or desktop tool.
2. Set the taste axes before talking about components.
3. Choose one dominant visual thesis for the screen. Do not stack multiple vibes.
4. Solve hierarchy, states, and platform fit before adding flourish.
5. Translate the direction into reusable tokens and component rules once the screen logic is working.

## Taste Axes

Set these five axes explicitly when the user has not already done it. They prevent vague "make it nicer" work.

| Axis | Low End | High End | What It Controls |
| --- | --- | --- | --- |
| Composure | restrained | theatrical | how loudly the interface performs |
| Density | spacious | operational | how much work fits into a screen |
| Contrast | soft | sharp | edge definition, hierarchy, and tension |
| Materiality | flat | layered | borders, shadows, blur, and surface depth |
| Motion | still | expressive | how much movement is used to explain state |

Use the axes as planning variables, not as decoration knobs. A dense desktop tool can still be calm. A marketing page can still be restrained.

## Operating Rules

1. Fit the product before fitting a trend. The right answer for a workflow tool is not the same as the right answer for a launch page.
2. Establish hierarchy at three distances: page structure, section structure, and component structure.
3. Treat states as part of the design, not implementation leftovers. Empty, loading, success, error, hover, focus, and selected states all count.
4. Use motion to clarify change, sequence, or causality. If motion exists only to look expensive, cut it.
5. Keep the visual vocabulary tight. Repetition creates identity; one-off flourishes create noise.
6. Prefer specific, believable copy and realistic data over placeholder language.

## Platform Guardrails

- Marketing web:
  - Allow more dramatic pacing and asymmetry.
  - Let imagery and motion carry more narrative weight.

- Product web:
  - Favor navigational clarity, repeated tasks, and fast scanability.
  - Keep decorative motion below the level of interaction feedback.

- Desktop:
  - Design for density, keyboard use, secondary controls, and longer sessions.
  - Do not import landing-page hero logic into tool surfaces.

Read `references/platform-adaptation.md` before applying a single visual language unchanged across all three.

## Review Questions

Before you finalize a direction, answer these:

1. What is the first thing the user should notice in under two seconds?
2. What would disappear if you removed 20% of the chrome?
3. Which states are still undesigned?
4. Does the interface feel like the product category, or like a generic AI demo?
5. Would this still hold up with real content, messy data, and long labels?

## Gotchas

1. A beautiful hero does not rescue a weak working surface.
2. Extra shadows do not create hierarchy if the grouping is wrong.
3. More accent colors usually reduce confidence rather than increase richness.
4. Dense interfaces fail from rhythm problems more often than from lack of whitespace.
5. Desktop tools need affordances for precision, not just prettier cards.
6. Motion without state logic reads as theater.
7. A design system created too early can freeze a bad direction into reusable parts.

## Reading Guide

| If the task is... | Read |
| --- | --- |
| "Give this project a stronger visual direction" | `references/principles.md`, then `references/style-families.md` |
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

