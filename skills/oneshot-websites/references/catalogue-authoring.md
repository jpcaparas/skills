# Prompt Catalogue Authoring

Read this file when adding, editing, or reviewing templates in `assets/prompt-catalogue.json`. The JSON file is the only canonical copy of the catalogue.

## Entry Contract

Every prompt entry has:

- `id`: a permanent identifier such as `ow-101`
- `slug`: a unique lowercase hyphenated label
- `title`: a short, literal display name that a hurried reader understands immediately
- `description`: a plain one-line explanation used in the catalogue menu
- `category`: an existing category ID, or a newly declared category
- `prompt`: the goal presented to the one-shot lead
- `tags`: a non-empty set of lowercase discovery terms

Every category is a display namespace with a lowercase hyphenated `id`, a short `title`, and a single-line `description` that explains the family of experiences it contains. The unfiltered catalogue prints these namespaces in declaration order and renders every prompt beneath exactly one of them.

The catalogue root has two single-line prompt-composition fields with different roles:

- `experienceDirection` is silent coordinator guidance, not content to append to the actual prompt. Keep it visually led and interaction-first: favor direct manipulation, responsive motion, spatial or ambient behavior, and memorable moments worth sharing; keep text concise unless the requested format genuinely depends on richer copy. Leave the technology, dependency, asset, and build choices to the one-shot lead.
- `completionMandate` defines lead-facing requirements inherited by every catalogue entry and custom refinement. Every finished actual prompt must explicitly reject shortcuts and cookie-cutter approximations, state that the skill imposes no token budget limit, and demand subject-specific completeness. Replicas, clones, and emulators require fidelity down to the smallest meaningful interactions; original experiences require equivalent depth across states, feedback, motion, atmosphere, and detail. Adapt the mandate naturally to the selected subject rather than pasting its root value as generic boilerplate.

For a selected entry, use its goal as source material and internalize only the guidance that fits that subject. Turn it into concrete, experience-specific possibilities rather than copying, labelling, or mechanically paraphrasing the shared direction. The literal `experienceDirection` value must never appear in the prepared lead prompt or `PROMPT.md`.

Append new entries at the end. Assign the next unused numeric ID and never renumber or reuse an existing ID. Entries `ow-001` through `ow-100` are the validator-frozen seed: do not edit, delete, replace, or reorder them. Categories may grow; the catalogue has a minimum release floor of 100 entries, not a maximum.

Schema 1.1 deliberately migrated the original seed's display titles and added plain descriptions while preserving every ID, slug, category, source prompt, and tag. Schema 1.2 added the root `completionMandate`, so all existing and future prompts inherit the full-depth, no-shortcuts, no-token-budget contract without rewriting or constraining their implementation-open source goals. A future user-authorized migration of an existing display contract must bump both the catalogue schema and package version, update the frozen digest, reconcile every title reference and eval, and document which compatibility fields remained stable. Ordinary catalogue additions never rebaseline the seed.

Write browsing metadata for speed. Keep titles at most six words and 48 characters; name the recognizable format directly, such as `First-Person Shooter Game`, `City Sound Map`, or `Bicycle Maintenance Club`. Keep descriptions at most 18 words and 140 characters. Say what the visitor does in ordinary language. Avoid lore names, coined brands, metaphors, mood-only labels, and decorative words that force readers to inspect the full prompt before understanding the option.

## Prompt Style

State the experience to create and the capability it should demonstrate. Leave the implementation open.

Good:

> Create a playable arena game where rocket-powered cars compete to drive an oversized ball into rival goals.

Over-constrained:

> Build a single-file React 19 game with Three.js, Tailwind, no external assets, and exactly four components.

The first prompt establishes the goal. The second spends the model’s judgement before it starts. Technology, dependency, file-layout, runtime, asset, duration, and workflow requirements belong only when the user’s actual experiment calls for them.

Keep each template self-contained, distinct from existing entries, and broad enough for stronger future agents to surprise the user. Let the shared `experienceDirection` guide prompt composition silently; do not repeat it in every goal, expose it as lead-facing boilerplate, or turn the catalogue into a hidden quality checklist. Let the root `completionMandate` supply the universal depth requirement at prompt-composition time, so future entries inherit it automatically without duplicating generic prose in every source goal.

Treat matching as relevance-gated. Offer an entry only when its core experience is materially useful for the request. Do not splice catalogue language into a custom brief merely because a tag, visual motif, or broad category overlaps. When no entry is a meaningful baseline, leave catalogue ideas out and refine only the user’s own guidance under the full-depth custom-prompt contract in `SKILL.md`; the universal `completionMandate` still applies because it governs build quality rather than subject matter.

## Add and Verify

1. Search titles, descriptions, slugs, prompts, and tags for overlap.
2. Append a new category with its one-line namespace description only when no existing category fits.
3. Append the prompt entry without editing stable IDs.
4. Run the package validator and listing tests.
5. Render the new entry through `scripts/list_prompts.py` and confirm it is understandable without surrounding notes.

The addition is complete when the JSON parses, every identity field is unique, each namespace and prompt renders with a plain title and scan-friendly description, the source prompt is goal-led and implementation-open, and existing entries are unchanged.

## See Also

- `references/research-notes.md` — inspiration and benchmark evidence
- `references/execution-protocol.md` — how a selected prompt becomes an isolated run
