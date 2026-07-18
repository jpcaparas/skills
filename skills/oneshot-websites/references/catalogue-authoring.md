# Prompt Catalogue Authoring

Read this file when adding, editing, or reviewing templates in `assets/prompt-catalogue.json`. The JSON file is the only canonical copy of the catalogue.

## Entry Contract

Every prompt entry has:

- `id`: a permanent identifier such as `ow-101`
- `slug`: a unique lowercase hyphenated label
- `title`: a short display name
- `category`: an existing category ID, or a newly declared category
- `prompt`: the goal presented to the one-shot lead
- `tags`: a non-empty set of lowercase discovery terms

Append new entries at the end. Assign the next unused numeric ID and never renumber or reuse an existing ID. Entries `ow-001` through `ow-100` are a validator-frozen seed: do not edit, delete, replace, or reorder them. Categories may grow; the catalogue has a minimum release floor of 100 entries, not a maximum.

## Prompt Style

State the experience to create and the capability it should demonstrate. Leave the implementation open.

Good:

> Create a playable arena game where rocket-powered cars compete to drive an oversized ball into rival goals.

Over-constrained:

> Build a single-file React 19 game with Three.js, Tailwind, no external assets, and exactly four components.

The first prompt establishes the goal. The second spends the model’s judgement before it starts. Technology, dependency, file-layout, runtime, asset, duration, and workflow requirements belong only when the user’s actual experiment calls for them.

Keep each template self-contained, distinct from existing entries, and broad enough for stronger future agents to surprise the user. Do not turn the catalogue into a hidden quality checklist.

Treat matching as relevance-gated. Offer an entry only when its core experience is materially useful for the request. Do not splice catalogue language into a custom brief merely because a tag, visual motif, or broad category overlaps. When no entry is a meaningful baseline, use the user’s guidance unchanged and leave the catalogue out of the dispatched prompt.

## Add and Verify

1. Search titles, slugs, prompts, and tags for overlap.
2. Append the new category only when no existing category fits.
3. Append the prompt entry without editing stable IDs.
4. Run the package validator and listing tests.
5. Render the new entry through `scripts/list_prompts.py` and confirm it is understandable without surrounding notes.

The addition is complete when the JSON parses, every identity field is unique, the prompt is goal-led and implementation-open, and existing entries are unchanged.

## See Also

- `references/research-notes.md` — inspiration and benchmark evidence
- `references/execution-protocol.md` — how a selected prompt becomes an isolated run
