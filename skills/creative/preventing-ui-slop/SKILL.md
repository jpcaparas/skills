---
name: preventing-ui-slop
description: "Prevents generic, decorative AI UI defaults. Use automatically for all UI work: designing, building, editing, reviewing, or prompting websites, apps, components, dashboards, and UI copy, including small changes. Applies alongside design skills; excludes backend-only work and non-UI illustrations or prose."
---

# Preventing UI slop

Make the interface serve its users, not advertise the agent's default aesthetic.
Apply these guardrails before generating UI and again before handing it off.

## Apply this to every UI task

This is a standing quality constraint, not an optional cleanup requested only by
the words “AI slop.” Use it for new interfaces, small component edits, redesigns,
reviews, UI copy, and UI-generation prompts. Pass the relevant constraints into
delegated briefs and image-generation prompts; another tool does not inherit
these instructions automatically.

Keep the check proportional to the affected surface. A button fix does not
authorize a site-wide redesign. Inspect existing components, tokens, content,
and the user task before choosing a treatment. Apply this alongside
`interface-design-taste` when available: that skill develops the visual direction;
this one prevents the failure modes below. It has no dependency on that skill.

## Do not introduce these defaults

“Modern,” “premium,” “polished,” “tech,” and an underspecified brief are not
permission to add these motifs. Choose structure, readable content, and useful
states first; do not decorate an empty section merely because it feels empty.

| Tell | Required replacement or decision |
| --- | --- |
| **Gradients everywhere**: gradient buttons, text, background blobs, or an automatic purple glow | Start with the product's surface and action tokens. Do not scatter gradients or blobs to manufacture interest. Retain a specifically requested brand treatment or a meaningful continuous data scale without spreading it to unrelated elements. |
| **Arbitrary rainbow colour**: each card, metric, or field gets a different hue without meaning | Give colour a consistent role: action, selection, status, category, or brand. Use labels or another cue alongside meaningful colour. Do not impose an invented palette ratio or strip necessary distinctions from charts. |
| **Pulsing badges and invented status**: decorative “Live,” “Active,” “Verified,” or “Secure” pills | Omit them unless they communicate a truthful, relevant state with an identified source. Explain what the state means when needed. Do not infer verification from login, a logo, or the existence of a profile. Prefer static feedback; reserve motion for actual, useful change and respect reduced motion. |
| **Fingernail cards**: repeated rounded cards with a narrow coloured edge, usually down the left | Use grouping, spacing, separators, lists, or tables when those express the relationship. Do not add the strip as a generic upgrade. Preserve an established semantic edge, such as incident severity, with a text label or other non-colour cue. |
| **Emoji decoration**: rockets, sparkles, and emoji on every heading, stat, or button | Use no icon unless it helps recognition, or use the product's consistent icon set with accessible names where needed. Preserve intentional emoji content, such as user reactions; do not use emoji to disguise empty copy. |
| **Misalignment**: floating SVGs, timeline marks, icons, ASCII art, or wrapped labels that drift | Align to actual content baselines and layout tracks. Test long labels, multiline rows, missing values, and narrow widths. Fix the layout rather than nudging one screenshot into place with arbitrary offsets. |
| **Automatic font personality**: Inter by reflex, monospace because “tech,” or decorative `//` prefixes | Inherit the product's readable type system. Use monospace for code or values that benefit from it; omit fake code syntax in ordinary headings. Inter and JetBrains Mono are valid when appropriate. Do not replace them with an illegible novelty font to look less generated. |
| **Chat-context leakage**: public copy about the owner's editor, framework, implementation instructions, or internal reorganisation | Write for the visitor's task. Keep authoring context out of the UI unless it is explicitly relevant public content. Do not turn “I write in Neovim” into a footer or an internal consolidation request into a marketing slogan. |
| **Default glassmorphism**: blurred translucent panels everywhere, or a stock brutalist makeover as the supposed cure | Use surfaces that preserve hierarchy and legibility. Glass and brutalism require an actual brief or established system, not a fallback style preset. Verify text and controls against the backgrounds they can really appear over. |
| **Generic hype and redundant introductions**: “Elevate,” “Seamless,” “Next-Generation,” “Supercharge,” “Unleash,” “Empower,” or “Welcome to your Dashboard ✨” | Say what the product does and what the user can do next. Omit subtitles that merely repeat the heading. A working screen needs working content, not a landing-page hero and an unsupported promise. Ordinary precise uses of a word are not offences. |

## Keep labels, themes, and tooling purposeful

- **Remove redundant eyebrows and ornamental numbering.** Do not put
  widely tracked, all-caps “FEATURES” above “Features,” or “02. ABOUT” on an
  unnumbered page just to imitate editorial design. A category label that adds
  information, real step numbers, and navigation landmarks can stay.
- **Do not force dark mode as the fashionable default.** Preserve the existing
  theme contract and explicit user choice. For a new themeable interface, honour
  the system preference and verify readable light and dark treatments. A local
  edit does not require inventing a theme system. An intentionally single-theme
  product still needs legible contrast; do not describe dual themes as a
  universal accessibility requirement.
- **Do not confuse tools with defects.** Vercel hosting, Tailwind, shadcn,
  Bootstrap, a popular font, purple, and em dashes do not prove AI authorship or
  poor usability. Judge the actual interface. Do not migrate hosting or replace
  a sound component library to hide its origin.

## Exceptions must have evidence, not an aesthetic excuse

The prohibited behaviour is adding the tell without purpose. Retaining a
specific user-requested design, a required existing system, or a truthful
semantic cue is different. Point to that requirement or meaning when the choice
would otherwise look like a violation. “It adds polish” is not evidence.

Do not use an exception to excuse false claims, broken alignment, unreadable
contrast, or inaccessible interaction. Do not silently remove a real state just
because a badge resembles an example. Keep an incident's “Investigating” status;
remove a made-up “Verified” badge. Keep a labelled severity stripe; remove a
decorative stripe from every profile field. Preserve a purple brand; omit the
unrequested purple glow. Avoid replacing every design with the same beige or
monochrome anti-slop template.

## Check the rendered result before calling UI work finished

For implementation, use the project's preview or browser workflow and inspect
the actual affected surface, not just source code or a generated mockup. For
visual changes, capture and inspect representative wide and narrow views, plus
the changed states. Exercise relevant long-content, empty, loading, error,
theme, and reduced-motion cases; choose cases that can expose this change's
failure rather than running an unrelated audit. Interaction-only changes need
DOM or accessibility checks and an exercised interaction, not decorative
screenshots.

Ask whether each accent, badge, card, icon, label, and motion has a defensible
role. Remove or repair unjustified tells in scope, then inspect again. In a
review-only task, report the observed defect and concrete correction without
editing. If rendering is unavailable, distinguish source inspection from visual
verification and name what remains unchecked. A screenshot cannot prove a
status is truthful; trace its data or state logic too.

For concept images, inspect the generated image against these guardrails and
revise material violations. A concept is a design reference, not proof of working
behaviour. Report consequential retained exceptions and verification limits;
do not append a ceremonial checklist to every small UI reply.

## Keep the guidance useful

These are design guardrails, not an AI-authorship detector or a universal design
standard. A discoverable skill guides an agent; it cannot guarantee invocation or
compliance by every future model.

When a rule conflicts with observed product needs or platform behaviour, consult
the existing design system and relevant official platform/accessibility guidance.
Propose a narrow canonical correction with the evidence and a counterexample;
do not silently rewrite an installed skill or publish an update.
