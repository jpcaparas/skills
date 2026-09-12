# Lean Text Rules

Use this reference when creating, editing, or auditing web pages that would otherwise accumulate filler copy, decorative labels, and placeholder-heavy sections.

## Default Stance

Start from the smallest useful text surface:

1. Name the thing.
2. State the user-visible value or task.
3. Provide the next action.
4. Add detail only when it changes comprehension, trust, accessibility, or task completion.

If a sentence does not answer "what is this?", "why does it matter?", "what can I do?", or "what must I know before acting?", remove it.

## Keep / Cut Table

| Text type | Default | Why |
| --- | --- | --- |
| H1 | Keep | Page identity and purpose |
| Hero support sentence | Keep one | Helps users decide whether they are in the right place |
| Eyebrow above every heading | Cut | Usually repeats section structure |
| Generic badges such as "New", "Powerful", "Trusted" | Cut | Adds noise without evidence |
| Feature card descriptions | Cut when repetitive | Card titles often carry the meaning alone |
| Client-provided copy | Keep unless asked to edit | User intent overrides the lean default |
| Form labels and legends | Keep | Required for comprehension and accessibility |
| Placeholder-as-label | Cut | Replace with visible label or persistent helper text |
| Legal, pricing, safety, consent text | Keep | Consequence-bearing text is not filler |
| Invented stats, quotes, names, logos | Cut | Unsupported social proof lowers trust |

## Copy Budgets

These are starting limits, not a scoring system. Exceed them only when the user asked for fuller copy or the page would become ambiguous without more words.

| Element | Budget | Good default |
| --- | --- | --- |
| H1 | 3-8 words or the product name | `Manage renewals without spreadsheet drift` |
| Hero support | 12-24 words | `Track contract dates, owners, and renewal risk from one operational view.` |
| Section heading | 2-7 words | `Renewals at risk` |
| Feature title | 2-5 words | `Owner follow-up` |
| Feature body | 0-14 words | `Escalate stale tasks before renewal windows close.` |
| Button | 1-3 words | `Create report` |
| Empty state heading | 2-6 words | `No renewals due` |
| Empty state body | 0-16 words | `Add a contract to start tracking renewal dates.` |

## Decorative Labels

Omit decorative label elements by default:

- `Features`
- `Benefits`
- `Solutions`
- `Platform`
- `Overview`
- `Why us`
- `New`
- `Introducing`
- `Trusted by`
- `Enterprise ready`
- `Testimonials`
- `FAQ`

Keep a label only when it has a distinct job:

- It differentiates state: `Beta`, `Draft`, `Paused`.
- It names a real category in a mixed set: `Finance`, `Operations`, `Security`.
- It is part of navigation or a table/filter system.
- The user explicitly asked for eyebrow labels, badges, tags, or chips.
- The surrounding design system already uses meaningful category labels.

## Placeholder Content

Use placeholders only when they are needed to render layout states. Keep the set small and domain-relevant.

Avoid:

- lorem ipsum
- `Feature one`, `Feature two`, `Card title`, `Short description`
- generic person names, quotes, avatars, and logos unless the section was requested
- invented metrics such as `99%`, `10x`, `2M+`, or `500+ teams`
- repeated "Learn more" links when the destination is not real

Prefer:

- realistic but modest sample row data when building tables
- one or two representative cards instead of six filler cards
- skeleton states or empty states when the content source is not known
- explicit notes in comments or code fixtures when content must be replaced later

## Forms And Inputs

Do not use this skill as a reason to strip form semantics.

Keep:

- visible labels for inputs, selects, textareas, radio groups, and checkbox groups
- legends for grouped controls
- `aria-label` only when a visible label is impossible or redundant with visible context
- `aria-describedby` for persistent helper text and error messages
- required/optional indicators when the distinction matters
- format examples outside the field when users must preserve a specific format

Avoid:

- placeholder text as the only label
- helper text that explains an obvious control
- hiding important instructions inside placeholders
- vague labels such as `Details`, `Info`, or `Value` when the domain has a clearer noun

## Audit Pass

Before finalizing a new page scaffold, scan for these signs of bloat:

1. More than one eyebrow or badge in the first viewport.
2. A repeated section pattern of label, heading, subtitle, and grid.
3. Feature cards whose descriptions restate their titles.
4. A page that includes testimonials, logos, stats, pricing, FAQ, and feature grids without being asked for a full landing page.
5. Paragraphs longer than two lines inside compact cards.
6. Buttons labelled `Learn more` without a real explainer destination.
7. Inputs with placeholders but no durable label or accessible name.

Use `scripts/audit_lean_text.ts` as a deterministic first pass. Treat its output as a review queue, then use judgment for user-requested exceptions.

## See Also

- `references/research.md` for source-backed rationale and accessibility boundaries.
