# Gotchas

## Hallucinated Intent

Symptoms:

- The document claims a target customer, roadmap, or business model that no file supports.
- The "purpose" section reads like startup positioning rather than a grounded repo briefing.

Fix:

- Downgrade unsupported claims to `Tentative` or `Open question`.
- Add evidence anchors to every important claim.
- Ask the user to confirm product intent after the draft exists.

## Architecture Inventory Masquerading as Intent

Symptoms:

- The doc lists directories and dependencies but never explains why the repository exists.
- Future agents would know the stack but not the product idea.

Fix:

- Move implementation details under "Architecture Map".
- Rewrite the executive read around user outcome, domain, and intended behavior.

## Overtrusting README Drift

Symptoms:

- README says one thing, but tests/routes/manifests show another active surface.
- The doc erases this tension and picks whichever source sounds cleaner.

Fix:

- Add a "Tension" or "Open question" entry.
- Preserve direct README claims as `Certain` only about what the README says, not necessarily what the current code does.

## Asking Before Looking

Symptoms:

- The agent asks "What is this repo for?" before inspecting files.
- The user has to restate information the code already contains.

Fix:

- Run the inventory script.
- Read explicit docs and manifests.
- Draft the doc first, then ask targeted questions tied to specific ambiguity.

## Treating User Corrections as Chat-Only Context

Symptoms:

- The user answers open questions, but the file remains unchanged.
- Future agents rediscover the same ambiguity.

Fix:

- Update `REPO_INTENT.md` immediately after answers.
- Add a review log entry naming the confirmed or corrected point.

## Accidental Agent-Instruction Changes

Symptoms:

- The agent edits `AGENTS.md` or `CLAUDE.md` while creating the intent doc, even though the user only asked for a draft.

Fix:

- Keep integration as a suggestion inside the intent doc.
- Ask before changing persistent agent instructions.
