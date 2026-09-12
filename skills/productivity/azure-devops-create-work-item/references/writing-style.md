# Work item writing style

Use this reference for the prose inside `work-item.md`, `context.md`, and `sources.md`. It adapts the durable parts of the Google developer documentation style guide to Azure DevOps work items.

This skill does not create or edit wiki pages. Apply these rules to the work item packet; route standalone documentation or wiki work to a documentation-writing workflow.

## Style precedence

Apply guidance in this order:

1. Preserve supplied facts, evidence, uncertainty, exact literals, and sensitive-data boundaries.
2. Follow the selected Azure Boards work item type, the fixed packet schema, and the organisation's process conventions.
3. Follow the project's approved terminology, template, locale, and house style.
4. Apply the adaptable documentation rules in this reference.

Do not import Google product wording, US English, or formatting that conflicts with Azure DevOps or local conventions. The existing NZ English contract for manual QA remains authoritative.

## Keep style separate from product scope

- Apply accessibility guidance to the writing and instructions. Do not turn a visual description in the notes into a new product accessibility requirement unless the source, user, or existing standard requires that change.
- Preserve colour, position, and other visual details when they are observed facts. Do not use them as the only procedural locator for the reader.
- Do not infer an eligibility rule, cutoff, owner, state transition, monitoring surface, error path, or business impact from suggestive wording. Record the ambiguity in `context.md` or ask for the missing fact.
- Do not add acceptance criteria or QA scenarios merely because they are common for similar work. Every required behaviour, boundary, and verification surface must come from the supplied context, repository evidence, or an explicit user decision.

## Write each field for its job

### Title

- Use sentence case unless the organisation requires another convention.
- Name the change, defect, or outcome with specific product language.
- Preserve supported prefixes such as `SECURITY:`, identifiers, version numbers, and proper nouns.
- Avoid generic titles such as `Updates`, `Improvements`, or `Fix issue`.

### Problem

- Lead with the observed need, defect, or delivery constraint.
- Name the affected role, workflow, service, or component.
- State the consequence in measurable or observable terms when the source provides them.
- Separate observation from inference. Do not present a suspected cause as established fact.
- Preserve ambiguous timing or scope as an open question; do not silently turn a date into a cutoff or eligibility rule.
- Keep proposed implementation out of the problem statement unless it is a fixed constraint.

### Reproduction Steps

- Put setup and preconditions before the actions that depend on them.
- Use a numbered list and start each required step with an imperative verb.
- Put the UI, tool, or environment before the action when location matters.
- Use exact visible labels and literal values.
- End with the observed incorrect result. Keep the expected fixed behaviour in `Outcome`, `Acceptance Criteria`, or `Test Scenario`.

### Action

- State the smallest useful delivery path rather than a file-by-file implementation diary.
- Use active verbs and name an owner or component when responsibility would otherwise be unclear.
- Put a condition before the action it governs.
- Label proposed or future work honestly. Do not write a plan as though it already happened.

### Outcome

- State what becomes observably true when the item is complete.
- Name the affected person, system, or delivery flow.
- Replace vague benefits such as `improves the experience` with the supported change in behaviour or result.

### Acceptance Criteria

- Make each required condition observable and testable.
- Ground every condition in supplied context, repository evidence, or an explicit user decision. If the source does not say how to observe a background effect, record the missing verification surface instead of inventing a dashboard, log view, or status.
- Use `must` for a requirement, `can` for a capability or permission, and `might` for a possibility. Avoid `should` when the criterion needs a clear pass or fail.
- Keep one behaviour or meaningful boundary per criterion.
- Include the relevant failure, empty, permission, or recovery state when it defines done.
- Do not prescribe implementation unless the implementation is itself a requirement.

### Developer Notes

- Use bullets for constraints, dependencies, ownership, rollout notes, open questions, and evidence-backed code references.
- Put filenames, paths, commands, configuration keys, API elements, and identifiers in code formatting.
- Use descriptive Markdown link text for incidents, pull requests, specifications, dashboards, and decisions. Avoid `click here`, `this page`, and exposed URLs when the renderer supports links.
- Use unambiguous dates and include a time zone when timing affects delivery. Prefer ISO `YYYY-MM-DD` for machine-adjacent records unless the organisation requires another form.
- Define uncommon abbreviations on first use and keep terminology consistent across all fields.

### Test Scenario

- Follow `references/output-packet.md` for the Manual QA Scenario Contract.
- Address the tester directly through imperative steps; name the customer, administrator, service, or system when describing observed behaviour.
- Put conditions and test data before the action they govern.
- Refer to controls by their exact visible label, not by colour, icon shape, or screen position alone. If the notes provide only a visual locator, use a bounded placeholder such as `[confirm visible label]` and record the gap; do not repeat the inaccessible locator or invent a label.
- State the visible or inspectable signal that proves the result.
- Do not invent a failure mode, data state, test clock, dependency, dashboard, log view, or recovery path to reach the scenario count. Ask for the missing detail or mark the scenario as incomplete.

## Mixed-audience clarity

- Use familiar, literal language and standard sentence order.
- Keep the main actor and action near the start of the sentence.
- Prefer active voice when responsibility matters; use passive voice when the actor is unknown, irrelevant, or deliberately de-emphasised.
- Avoid idioms, slang, culture-specific humour, and claims that a task is easy, quick, or simple.
- Repeat a precise noun when `it`, `this`, `that`, or `they` could refer to more than one thing.
- Keep list items parallel and use numbered lists only when sequence or priority matters.
- Do not rely on colour, position, or an image as the sole evidence for a requirement or test result.

## Work item style gate

Before finalising `work-item.md`, confirm that:

- local process, terminology, locale, and packet schema override generic style preferences
- the title is specific and uses sentence case where local style permits
- the problem names the affected actor or component and the supported impact
- observations, assumptions, and proposals remain distinct
- style guidance has not introduced new product requirements or inferred rules
- prerequisites and conditions precede dependent actions
- acceptance criteria are observable and testable
- links name their destinations, dates are unambiguous, and literals remain exact
- missing UI labels and other required details are recorded instead of guessed
- the same concept uses the same term across the packet
- manual QA steps remain UI-driven, accessible, and verifiable
- every acceptance criterion, edge case, and verification surface is supported or explicitly marked missing

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

Google's guide addresses public developer documentation rather than Azure Boards. These rules are adaptations for backlog prose; Azure Boards semantics, organisation-specific workflow, and the packet contracts remain authoritative.
