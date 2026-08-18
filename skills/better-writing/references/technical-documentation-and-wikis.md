# Technical documentation and wikis

Use this reference when drafting, rewriting, or reviewing technical documentation or wiki entries. Use `references/genre-modes.md` to choose the page shape; this file adds documentation-specific style and maintenance rules.

The guidance adapts the durable parts of the Google developer documentation style guide. It does not import Google's product terminology, US English requirement, word list, or platform-specific formatting.

## Apply the right style hierarchy

Use this order of authority:

1. Preserve source truth, exact literals, and safety or legal requirements.
2. Follow the destination's templates, renderer constraints, repository conventions, glossary, locale, and house style.
3. Apply this reference where the preceding authorities do not settle the choice.
4. Use a general language reference only for remaining questions.

Depart from a preference when the audience or domain needs something clearer. Keep the exception consistent within the page or documentation set.

## Establish the page contract

Before drafting, identify:

- the reader and what they are trying to accomplish or understand
- the page mode: task, reference, explanation, decision, runbook, or another mode from `references/genre-modes.md`
- the starting state, prerequisites, permissions, and tools
- the canonical terminology and any terms that need definition
- the evidence source, owner, status, and review date when the wiki supports those fields
- the expected finish line or decision

Do not hide a required prerequisite in a later step. Do not invent an owner, review date, or status when the source does not provide one.

## Make navigation carry meaning

- Use sentence case for page titles and headings unless the destination requires another convention.
- Make the title describe the page's primary purpose.
- Start task headings with a base-form verb: `Configure single sign-on`, not `Configuring single sign-on`.
- Use a noun phrase for a conceptual heading: `Token expiry behaviour`, not a vague label such as `Overview` when a more specific phrase fits.
- Keep required articles such as `a`, `an`, and `the` when omitting them would make a heading clipped or ambiguous.
- Keep heading levels hierarchical. Do not skip levels merely to obtain a visual size.
- Avoid links, terminal punctuation, and overloaded abbreviations in headings.
- Define an abbreviation on first use unless the abbreviated form is more familiar to the audience than its expansion.

A reader scanning only the title and headings should understand the page's scope and route through it.

## Write procedures that can be executed

For a task, tutorial, or runbook:

1. State the outcome and starting context.
2. Put prerequisites and permissions before the steps.
3. Put a condition before the action it governs: `If the account uses SSO, select ...`.
4. Start each required step with an imperative verb.
5. Keep one reader decision or meaningful action in each numbered step. Combine tiny UI actions only when splitting them would make the procedure harder to follow.
6. State the tool, page, or field before the action when the location matters: `In the Azure portal, select ...`.
7. Mark a genuinely optional step with `Optional:` at the start.
8. Introduce a command by its purpose, not with an empty phrase such as `Run the following command`.
9. Show the expected result and a way to verify success.
10. Add recovery or rollback only when the source supports it.

Do not use `please` to soften a required step. Keep courtesy in the surrounding tone, not inside every instruction.

## Keep actors, terms, and requirements precise

- Address the reader as `you` in instructions when doing so makes responsibility clear.
- Name the actual role, team, service, or component when describing system behaviour. Avoid ambiguous `we`, `they`, `it`, or `the user`.
- Prefer active voice when the actor matters. Keep passive voice when the actor is unknown, irrelevant, or intentionally de-emphasised.
- Use present tense for current behaviour. Label proposals, planned behaviour, and future work as such.
- Use one term for one concept. Match exact UI labels, API names, product names, and glossary terms.
- Define uncommon abbreviations and necessary jargon on first use.
- Use `must` for a requirement, `can` for capability or permission, and `might` for possibility. Avoid `should` when the reader needs to know whether something is required or recommended.
- Preserve standards-defined meanings such as RFC requirement keywords when they are in scope.

## Write for a global audience

- Prefer familiar, literal words and standard sentence order.
- Keep the main subject and verb near the start of the sentence.
- Avoid idioms, slang, culture-specific humour, seasonal assumptions, and unexplained metaphors.
- Do not call a task easy, quick, or simple unless evidence and audience context support the claim.
- Repeat a noun when a pronoun would have more than one plausible antecedent.
- Use unambiguous dates and include a time zone when timing could affect execution. Prefer ISO `YYYY-MM-DD` in technical metadata, logs, and machine-adjacent records unless local convention requires another form.
- Follow the requested locale and house spelling. Do not replace NZ, Australian, British, or another established English variety merely because Google's source guide uses US English.

## Use lists, tables, links, and literals deliberately

- Use numbered lists for ordered actions or ranked priorities and bullets for unordered peers.
- Introduce a list or table with enough context to explain why it exists.
- Keep list items parallel in grammar, logical category, capitalization, and punctuation.
- Do not use a one-item list.
- Use a table when readers must compare several properties across several items. Avoid tables for long prose or sequential procedures.
- Use descriptive link text that names the destination or purpose. Avoid `click here`, `this page`, raw URLs, and repeated generic `Learn more` links.
- Explain downloads, external destinations, or other surprising link behaviour when it matters.
- Put paths, commands, filenames, configuration keys, API elements, and code identifiers in code formatting where the destination supports it.
- Introduce code blocks with the action or purpose they serve. Preserve the code exactly.

## Keep the page accessible and durable

- Do not rely on colour, position, shape, sound, or an image as the only carrier of meaning.
- Give images and diagrams useful alternative text or an adjacent text explanation.
- Refer to controls by their exact visible label, not by location or icon shape alone. If the source provides only a directional or visual description, replace it with a bounded placeholder such as `[confirm visible label]` and record the gap. Do not repeat the inaccessible locator as the instruction or invent a plausible label.
- Avoid directional references such as `above`, `below`, `on the right`, or `the green button`. Name the section, table, figure, or control instead.
- Make headings and links meaningful out of context for screen-reader and scanning workflows.
- Prefer one canonical explanation over copied wiki fragments that will drift. Link to the source of truth and state what the current page adds.
- Mark assumptions, decisions, deprecations, and time-sensitive facts explicitly. Add an owner or last-reviewed date only when the wiki has a real maintenance practice for those fields.
- Remove stale promises and unsupported future tense. Work that is merely proposed belongs in a clearly labelled plan, decision, or backlog item.

## Documentation gate

A documentation or wiki page passes when:

- its local style, locale, and exact terminology take precedence over generic guidance
- the reader, purpose, starting state, and finish line are clear
- headings form a useful navigation outline
- prerequisites and conditions appear before dependent actions
- procedures use imperative, verifiable steps
- actors, terms, dates, requirements, and future status are unambiguous
- links describe their destinations and literals remain exact
- missing UI labels and other required source details are marked instead of guessed
- the page remains understandable without colour, position, or images alone
- the content has a credible maintenance boundary and does not duplicate a canonical source without reason

## Source adaptation

This reference was reviewed against the following official Google developer documentation style pages on 2026-08-19:

- [About this guide](https://developers.google.com/style/)
- [Highlights](https://developers.google.com/style/highlights)
- [Voice and tone](https://developers.google.com/style/tone)
- [Active voice](https://developers.google.com/style/voice)
- [Write for a global audience](https://developers.google.com/style/translation)
- [Headings and titles](https://developers.google.com/style/headings)
- [Procedures](https://developers.google.com/style/procedures)
- [Lists](https://developers.google.com/style/lists)
- [Cross-references and linking](https://developers.google.com/style/cross-references)
- [Write accessible documentation](https://developers.google.com/style/accessibility)
- [Prescriptive documentation](https://developers.google.com/style/prescriptive-documentation)

The adaptation keeps the source guide's reader-first clarity, consistency, global-audience, procedural, linking, and accessibility principles. It deliberately leaves Google-specific branding, product wording, US English, and platform presentation rules behind.
