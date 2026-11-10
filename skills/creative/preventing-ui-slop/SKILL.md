---
name: preventing-ui-slop
description: "Prevents generic, decorative AI UI defaults. Use automatically for all UI work: designing, building, editing, reviewing, or prompting websites, apps, components, dashboards, and UI copy, including small changes. Applies alongside design skills; excludes backend-only work and non-UI illustrations or prose."
---

# Preventing UI slop

A standing constraint on every UI task, whether or not anyone says "AI slop": new interfaces, small edits, reviews, UI copy, and prompts for image or UI generators. Pass the relevant tells below into delegated briefs and image prompts, because another tool does not inherit this skill. Scale the check to the surface: a button fix does not authorise a redesign. Read the existing components, tokens and content first. It works alongside `interface-design-taste`, which chooses the visual direction; this skill only blocks the failures below.

"Modern", "premium", "polished", "tech" and an underspecified brief are not permission to add any of these. Do not decorate a section because it feels empty.

## Tells to leave out

- **Gradients everywhere**: gradient buttons, gradient text, background blobs, an automatic purple glow. Start from the product's surface and action tokens. Keep a gradient the user asked for as brand treatment, or one that is a real continuous data scale.
- **Arbitrary rainbow colour**: a different hue per card, metric or field. Give each colour one role (action, selection, status, category, brand) and pair meaningful colour with a label or other cue. Do not strip distinctions a chart needs.
- **Pulsing badges and invented status**: decorative "Live", "Active", "Verified", "Secure" pills. Show a state only if it is true and has an identifiable data source; never infer "verified" from a login, a logo or the existence of a profile. Use static feedback unless something actually changed, and respect reduced motion.
- **Fingernail cards**: repeated rounded cards with a narrow coloured edge, usually on the left. Use spacing, separators, lists or tables for grouping. An established semantic edge, such as incident severity, stays, with a text label so colour is not the only cue.
- **Emoji decoration**: rockets and sparkles on headings, stats and buttons. Use an icon only where it aids recognition, from the product's own icon set with accessible names. Intentional emoji content, such as reactions, stays.
- **Misalignment**: floating SVGs, timeline marks, icons, ASCII art or wrapped labels that drift. Align to real baselines and layout tracks, and test long labels, multiline rows, missing values and narrow widths. Fix the layout instead of nudging with arbitrary offsets.
- **Font personality by reflex**: Inter by default, monospace because "tech", decorative `//` prefixes. Inherit the product's type system. Monospace is for code and values that benefit from it. Inter and JetBrains Mono are fine when they fit; do not swap them for an illegible novelty face to look less generated.
- **Chat-context leakage**: public copy about the owner's editor, framework, instructions to the agent, or an internal reorganisation ("I write in Neovim" in a footer, "we consolidated three apps" as a slogan). Write for the visitor's task.
- **Default glassmorphism or stock brutalism**: blurred translucent panels everywhere, or brutalism as the supposed cure. Use them only for an actual brief or existing system, and check text and controls against every background they can sit over.
- **Hype and redundant intros**: "Elevate", "Seamless", "Next-Generation", "Supercharge", "Unleash", "Empower", "Welcome to your Dashboard ✨". Say what the product does and what the user can do next. Drop subtitles that repeat the heading. A working screen needs working content, not a landing-page hero. A precise ordinary use of one of these words is fine.
- **Redundant eyebrows and ornamental numbering**: tracked all-caps "FEATURES" above "Features", or "02. ABOUT" on an unnumbered page. Labels that add information, real step numbers and navigation landmarks stay.

## Not defects

- Dark mode is not a fashionable default. Keep the existing theme contract and explicit user choices. For a new themeable interface, honour the system preference and check both themes are legible. A local edit does not need a theme system, and a deliberately single-theme product only needs adequate contrast; dual themes are not a universal accessibility requirement.
- Vercel, Tailwind, shadcn, Bootstrap, a popular font, purple and em dashes do not prove poor usability. Judge the interface. Do not migrate hosting or replace a sound component library to hide where it came from.
- Avoid swapping every design for the same beige or monochrome anti-slop template.

## Exceptions need evidence

Retaining a tell is acceptable when a user-requested design, a required existing system or a truthful semantic cue demands it; point to that requirement. "It adds polish" is not evidence, and no exception covers false claims, broken alignment, unreadable contrast or inaccessible interaction. Keep an incident's "Investigating" status and a labelled severity stripe; remove a made-up "Verified" badge and a decorative stripe on every profile field; keep a purple brand and drop the unrequested purple glow.

## Checking the result

Inspect the rendered surface with the project's preview or browser workflow, not only the source: wide and narrow views plus the states you changed, choosing long-content, empty, loading, error, theme and reduced-motion cases that could expose this change's failure. Interaction-only changes need DOM or accessibility checks and an exercised interaction. A screenshot cannot prove a status is truthful, so trace its data or state logic. For concept images, inspect the output against these tells and regenerate on material violations; a concept is a reference, not proof of behaviour.

In a review-only task, report the observed defect and the concrete correction without editing, and do not invent rendered evidence you did not see. If rendering is unavailable, say which checks were source-only. Mention retained exceptions and verification limits in the reply, but do not append a checklist to small UI replies.
