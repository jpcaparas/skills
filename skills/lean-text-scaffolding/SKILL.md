---
name: lean-text-scaffolding
description: "Prevent bloated text scaffolds in new web pages. Use when creating or refactoring landing pages, SaaS pages, dashboards, marketing sections, UI copy, placeholders, labels, eyebrow text, feature cards, or scaffold content. Enforce concise, specific, necessary text and remove generic labels unless explicitly requested. Do NOT use for prose-only articles, legal copy, or preserving exact client-provided copy."
compatibility: "Requires: python3 for validation; optional bun for running scripts/audit_lean_text.ts directly."
metadata:
  version: "1.0.0"
references:
  - rules
  - research
---

# Lean text scaffolding

Keep newly scaffolded web pages from filling up with verbose filler, generic placeholder words, decorative labels, and repeated eyebrow text.

## Decision tree

What are you building or editing?

- A new web page, landing page, product page, dashboard, or section with generated copy
  Apply the lean baseline in this file, then read `references/rules.md` for detailed budgets.

- An existing page feels wordy, generic, or crowded with labels
  Read `references/rules.md`, remove low-value text, then run `scripts/audit_lean_text.ts` on changed HTML/JSX/TSX files when Bun is available.

- A page contains forms, filters, search, settings, or other inputs
  Preserve visible or accessible labels, legends, helper text, and error instructions. Read `references/research.md` if tempted to replace labels with placeholders.

- The user explicitly asks for detailed copy, labelled sections, content placeholders, a copy deck, SEO text, legal copy, or client-provided wording
  Follow the request. Keep the content organized, but do not enforce the lean default against explicit requirements.

- The task is prose-only, documentation-only, or non-web copy
  Do not trigger this skill. Use a writing or documentation skill instead.

## Quick reference

| Situation | Default action | Read / run |
| --- | --- | --- |
| New scaffolded page | Start with fewer words, fewer sections, and no decorative labels | `references/rules.md` |
| Hero copy | One clear H1 plus one support sentence unless asked for more | `references/rules.md` |
| Feature cards | Use concrete short headings; omit generic card descriptions | `references/rules.md` |
| Eyebrows, badges, chips | Omit by default unless they disambiguate state, category, or navigation | `references/rules.md` |
| Forms and inputs | Keep labels, legends, helper text, errors, and accessible names | `references/research.md` |
| Auditing source files | Flag filler phrases, label spam, long paragraphs, and placeholder-only inputs | `scripts/audit_lean_text.ts` |

## Lean baseline

Use these defaults when the user has not explicitly asked for fuller copy:

1. Write only the text needed to understand or operate the page.
2. Prefer one strong heading over an eyebrow plus heading plus subtitle stack.
3. Avoid generic section labels such as "Features", "Benefits", "Solutions", "Testimonials", "New", or "Trusted by" unless the label changes user understanding.
4. Avoid filler placeholders: lorem ipsum, "Feature one", "Powerful insights", "Everything you need", "All-in-one platform", "Seamless workflows", and similar stock phrases.
5. Do not invent stats, logos, testimonials, names, quotes, badges, or social proof to make a scaffold feel full.
6. Keep essential UI text: navigation labels, button text, table headers, form labels, helper text, validation errors, empty states, and screen-reader names.
7. If a page needs realistic sample data to render a state, use the smallest representative set.

## Default copy budgets

| Element | Default budget |
| --- | --- |
| H1 | Brand/product name or 3-8 clear words |
| Hero support | 1 sentence, usually 12-24 words |
| Section heading | 2-7 words, no separate label unless needed |
| Feature card title | 2-5 words |
| Feature card body | 0-14 words; omit if it repeats the title |
| CTA | 1-3 action words |
| Empty state | 1 heading plus 1 short recovery action |
| Form helper text | Only when format, consequence, or requirement is not obvious |

## Required preservation

Lean text does not mean unlabeled UI. Preserve or add:

- `<label>` and `<legend>` text for form controls
- `aria-label`, `aria-labelledby`, and `aria-describedby` when visible text is absent or insufficient
- visible helper text for uncommon formats, required/optional distinctions, destructive actions, and errors
- link and button text that makes sense out of context
- regulatory, pricing, contract, consent, or safety wording supplied by the user

## Workflow

1. Before scaffolding, infer the page job and the user-supplied content.
2. Build the smallest credible page that satisfies the request.
3. Remove decorative labels, repeated subtitles, generic cards, invented social proof, and filler sections.
4. Preserve accessibility and operational text.
5. If source files exist and Bun is available, run:

```bash
bun scripts/audit_lean_text.ts path/to/page.tsx
```

6. Fix every issue that is not explicitly justified by the user's request.

## Reading guide

| Need | Read |
| --- | --- |
| Detailed keep/cut rules, copy budgets, and audit heuristics | `references/rules.md` |
| Source-backed rationale and accessibility boundary | `references/research.md` |
| Deterministic file audit for HTML/JSX/TSX | `scripts/audit_lean_text.ts` |

## Gotchas

1. **Do not remove real labels to make a page look cleaner.** Decorative badges are optional; input labels and accessible names are not.
2. **Do not replace real content with vagueness.** "Concise" means specific in fewer words, not generic.
3. **Do not add fullness theater.** Extra testimonials, stats, badges, FAQs, logos, and comparison blocks make a scaffold look busier but less trustworthy when unsupported.
4. **Do not fight explicit copy requests.** If the user asks for detailed marketing copy, labelled sections, or placeholder content, satisfy that requirement and keep structure clean.
5. **Do not hide necessary instruction inside placeholders.** Placeholder text disappears and is a poor substitute for labels or persistent hints.
