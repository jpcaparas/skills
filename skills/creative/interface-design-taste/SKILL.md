---
name: interface-design-taste
description: "Design high-quality product apps, marketing sites, dashboards, and desktop UI. Use for art direction, critique, redesign, hierarchy, layout, typography, color, motion, or lightweight design systems. Do NOT use for logos, illustration-only work, image prompts, or backend-only tasks."
---

# Interface design taste

Fit the product, the task and the requested character before any trend. Preserve the user's intent instead of substituting a house style; mixed styles, bold palettes, dark canvases and expressive motion are all fine when hierarchy, contrast and usability survive. `preventing-ui-slop` blocks the generic AI defaults; this skill chooses the direction.

## Direction

Resolve the artifact (marketing page, content page, product surface, dashboard, desktop tool), the user's goal on the screen, how often they see it, and whether they are browsing, deciding, operating or monitoring. Skip any worksheet when the brief already gives direction. For vague "make it nicer" requests, these axes make a direction concrete: composure (restrained to theatrical), density (spacious to operational), contrast (soft to sharp), materiality (flat to layered), motion (still to expressive). They are discussion aids, not scores. A dense desktop tool can be calm; a marketing page can be restrained.

Starting points to adapt, not a menu:

- Editorial Calm: reading-heavy products. Refined sans with restrained serif accents, quiet borders, one muted accent, slow subtle motion.
- Product Precision: B2B, fintech, dashboards. Sharp sans with mono for numbers, crisp dividers, disciplined cards, short state-led motion.
- Warm Material: consumer, wellness, creative tools. Humanist type, soft layered surfaces, fluid motion; watch for shadows that blur object boundaries.
- Operational Density: admin panels, ops consoles, desktop tools. Compact sans plus mono, dividers over cards, minimal ornament, fast motion.
- Expressive Showcase: launches, portfolios, campaigns. Bold display type, one dominant visual idea per section, high-energy motion; keep text readable, no unsafe flashing, reduced-motion alternative.

## Hierarchy and layout

- Judge hierarchy at three levels: screen frame (what is fixed, what scrolls), section grouping, component internals (label, value, action, metadata, state). If they disagree the screen is noisy whatever the colours.
- Usually one zone dominates (hero claim, canvas, table, form sequence). Monitoring and comparison views may need equal peers; make their relationships explicit.
- Whitespace helps only when patterned: related items closer than unrelated ones, bigger gaps at hierarchy changes, not equal spacing everywhere. Asymmetry must increase focus or pacing.
- Cards are not a default. On operational screens, structure from lines, panes or grouped rows often beats cards. Use cards for reorderable units, elevation over busy fields, modular previews and touch grouping.
- Cramped screen: remove repeated chrome before shrinking type, collapse decorative wrappers before shrinking hit areas, align numbers and actions on vertical rails, reserve high-emphasis colour for status and actions.
- Responsive collapse goes multi-panel, then two-zone, then one clear column. Keep the primary task path, keep controls near the object they affect, simplify asymmetry early. Do not just stack in source order.
- Promotional hero: headline readable at a glance, no six-line heading blocks when width is available.

## Type and copy

- Define roles before fonts: display (sparingly), UI sans, body, mono (code, timestamps, IDs, metrics, aligned numbers). Keep display personality out of forms, settings and data tools.
- Reduce the number of text sizes; tighten the gap between primary and secondary roles; shorten labels before shrinking fonts. Helper and error text must stay readable, not merely smaller. Drop decorative all-caps metadata unless it adds structure.
- Labels name the thing and distinguish similar controls. "Optimize", "Manage", "View Details", "Learn More" become "Retry sync", "Export CSV", "Pin column", "Show failed jobs".
- Copy is specific, calm, believable and scannable. Avoid startup clichés, invented certainty, placeholder names and perfect round numbers. Use realistic data.

## Colour, surfaces, icons, imagery

- A restrained starting palette: canvas, surface and text neutrals, one primary accent, semantic status colours. More colour is fine when essential signals keep recognisable roles and contrast stays readable.
- Spend the primary accent on main actions, focus, active selection and one or two highlights. If it also appears on decorative gradients, unrelated tags and every chart series, it stops signalling.
- Chart with one takeaway: neutral baseline, accent on the key series, semantic colour only for status or thresholds. Comparisons can use a categorical palette with labels or other non-colour cues. Do not let the chart out-shout the decisions around it.
- Pick materiality on purpose: lines and dividers for tools, selective cards for broad product UI, layering and blur only where warmth or theatre helps. If everything floats nothing is important. Do not use heavy borders and heavy shadows together. Shadows do not fix wrong grouping; alignment, spacing and headings do.
- Dark mode needs retuned neutrals, text contrast, border strength and emphasis, not an inverted light mode.
- Icons share stroke weight, corner logic and detail level, and support labels rather than replace them on first exposure. Imagery reinforces the product story and does not rescue an empty layout; in product apps prefer real product views over lifestyle stock.

## States and motion

- Design the whole state model: idle, hover, focus, pressed, selected, disabled, loading, empty, success, error. A component that only looks designed when nothing is happening is unfinished. Finish states before choreography.
- Loading matches the final layout's shape. Empty explains what the object is and gives one next action. Error says what failed and what to do, locally. Forms: label above the field, helper text for ambiguous choices, inline errors, success that differs from idle; no placeholder-only instructions.
- Motion tiers, mixable: still (dense tools, critical flows), supportive (most product apps: staggered entry, panel transitions), expressive (launches, storytelling). Expressive motion is allowed in products if it never delays actions, moves targets or loses the user's place. In dense apps animate opacity and transform, keep transitions short, and never make table or panel content lose position.
- Keep timings consistent across a family of actions, support keyboard and assistive states, provide reduced-motion alternatives and pause controls where needed, and keep essential information available without animation.

## Platform

- Marketing web: more dramatic pacing, bigger type contrast, expressive motion in hero and transitions; avoid app density and many equal cards.
- Web app: reliable navigation, fast scanning, predictable forms and filters, calmer system, tight accent and motion control; no landing-page hero logic in core areas.
- Desktop: split panes, inspectors, utility rails, dense regular spacing, keyboard support, hover/selection/focus that support precision, restrained depth. Avoid giant marketing type, oversized cards, soft luxury treatments that hide structure, and animation that breaks focus. Design for awkward window widths and let important panels keep width before decorative sections.
- Across web and desktop keep type and colour logic; let density, chrome and interaction depth diverge.

## Critiquing an existing interface

Audit by leverage, but prioritise observed task failures and the requested scope over completing every category: product fit, information hierarchy, layout and grouping, typography and labels, colour and surfaces, states, motion, polish. If the first three are weak, polish only hides it. Record the user's goal, the dominant object or action, what is emphasised now, the main friction, missing states and any platform mismatch. Report a short diagnosis, findings ordered by severity (blocker, high, medium, low), and the highest-leverage fixes without filling a quota. Do not rewrite from zero when asked what to fix first. Fix structure before softening the material language, and do not let a critique be styling-only.

Two diagnostics, neither a pass/fail gate: what should the user notice in under two seconds, and what would disappear if 20% of the chrome were removed. Also ask which states are undesigned, whether it feels like its product category or a generic AI demo, and whether it holds with real content, messy data and long labels.

## Design-system capture

Capture tokens and component rules only when reuse or handoff needs them, and reuse an existing system where one exists. A system locked too early freezes a bad direction. Useful categories: type roles, spacing rhythm, radius, borders and dividers, surface hierarchy, accent usage, motion tiers, state treatments, and component behaviour (buttons, fields, cards, tables, navigation) rather than appearance alone. A one-off flourish can stay local.

## Failure modes

- A premium hero over generic cards inside: design the working surface first, let marketing inherit.
- Everything is boxed yet nothing is prioritised: re-establish dominant and supporting zones before choosing card styles.
- Every section is a designed moment: keep most of the interface disciplined so a few areas carry character.
- Looks premium only with fake content: test long labels, messy numbers, realistic empty states.
- Desktop treated like a phone mockup: add density, pane logic and precision affordances.
- Looks borrowed from a trend board: restate the product job and cut motifs that do not serve it.

If this guidance conflicts with observed behaviour, check current official platform or accessibility documentation and propose a sourced correction; do not edit installed copies.
