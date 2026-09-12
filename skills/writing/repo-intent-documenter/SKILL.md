---
name: repo-intent-documenter
description: "Create evidence-backed repository intent docs for AI coding agents, including certainty levels, evidence anchors, open questions, and review workflow. Trigger on document repo intent, REPO_INTENT.md, or what this repo is for. Do NOT use for ordinary README polishing."
compatibility: "Requires: python3 for scripts/repo_intent_inventory.py, scripts/validate.py, and scripts/test_skill.py."
metadata:
  version: "1.0.0"
references:
  - methodology
  - document-contract
  - gotchas
---

# Repo Intent Documenter

Build a grounded repository intent document that makes the project's purpose, assumptions, and unresolved questions obvious to future agents.

## Decision Tree

What is the user asking for?

- Create or refresh a repo intent doc
  Run `scripts/repo_intent_inventory.py`, inspect the codebase, then write or update `REPO_INTENT.md`.

- Explain intent inline without writing files
  Use the same evidence model, but answer in chat and offer a doc path only if useful.

- Continue from an existing intent doc
  Read the existing doc first, preserve confirmed statements, and only revise claims contradicted by current evidence.

- User wants the doc opened after drafting
  Write the doc first, then open it with the available local mechanism. If no desktop opener exists, report the absolute path.

- The repository is missing or inaccessible
  Ask for the repo path or files. Do not invent intent from a project name alone.

## Quick Reference

| Need | Do |
|---|---|
| Fast repo map | `python3 scripts/repo_intent_inventory.py <repo> --json` |
| Evidence rules | Read `references/methodology.md` |
| Output shape | Start from `templates/repo-intent.md` and read `references/document-contract.md` |
| Ambiguity handling | Ask targeted questions after the draft, not before the first inspection |
| Failure modes | Read `references/gotchas.md` |

## Default Workflow

1. Resolve the repository root. Prefer the current working directory when it contains `.git`, a manifest, or existing project docs.
2. Run `python3 scripts/repo_intent_inventory.py <repo> --json` to collect the first pass of docs, manifests, tests, CI, entrypoints, and agent instructions.
3. Read the highest-signal files yourself: root README, AGENTS or CLAUDE files, package manifests, CI workflows, top-level source entrypoints, tests, examples, and existing docs.
4. Draft `REPO_INTENT.md` using `templates/repo-intent.md`.
5. Label claims as `Certain`, `Strong inference`, `Tentative`, or `Open question`. Every important claim needs an evidence anchor.
6. Ask the user only the questions needed to turn tentative claims into confirmed intent.
7. When the user answers, update the document and record the confirmation in the review log.
8. If requested, open the document for review after writing it.

## Evidence Standard

Separate direct evidence from interpretation:

- `Certain` means a source file, README, manifest, test, or config states it directly.
- `Strong inference` means multiple independent signals point to the same intent.
- `Tentative` means the claim is plausible but based on weak or single-source evidence.
- `Open question` means the agent should not present the claim as true until the user answers.

Use file anchors whenever possible, such as `README.md`, `package.json`, `src/server.ts`, or `tests/auth.test.ts`. Include line numbers when the harness can provide them cheaply.

## Output Path Policy

Default to `REPO_INTENT.md` at the repository root because future agents are most likely to discover a root-level intent file. Use `docs/repo-intent.md` only when the repository clearly keeps all durable project docs under `docs/` and root-level docs would violate local conventions.

Do not automatically edit `AGENTS.md`, `CLAUDE.md`, or other persistent agent instructions unless the user asks. Instead, add a short "Suggested integration" note in the intent doc when linking it from agent instructions would help.

## Question Protocol

Ask questions after the first draft exists, so the user can correct a concrete artifact.

Keep questions:

- evidence-linked: mention the file or signal that created the ambiguity
- answerable: prefer a short choice or factual confirmation
- prioritized: ask the smallest set that would materially improve future agent behavior
- non-blocking: leave unresolved questions in the doc if the user is not ready to answer

## Gotchas

1. Do not turn directory names into product strategy. `src/app` proves structure, not customer intent.
2. Do not flatten uncertainty. A confident but unsupported sentence is worse than an explicit open question.
3. Do not ask broad discovery questions before reading the repo. The point is to make the agent do the first pass.
4. Do not overwrite confirmed human intent just because current code is incomplete.
5. Do not bury the actual purpose under a long architecture inventory. Architecture supports the intent; it is not the intent.

## Reading Guide

| Need | Read |
|---|---|
| Full inspection method, signal ranking, and confidence labels | `references/methodology.md` |
| Required document sections, destination rules, and review loop | `references/document-contract.md` |
| Pitfalls and recovery patterns | `references/gotchas.md` |
| Starting Markdown shell | `templates/repo-intent.md` |
