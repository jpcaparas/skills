---
name: azure-devops-create-work-item
description: "Draft local Azure DevOps work item packets from loose context, defaulting to Scrum PBI unless Bug, Feature, User Story, Task, Issue, or Epic is specified. Inspect repo context when present. Do NOT use for live REST/CLI creation, migration, wiki, or status reporting."
compatibility: "Requires: python3. Optional network access only when re-checking Microsoft Learn documentation."
metadata:
  version: "1.1.0"
  repo_tags:
    - azure-devops
    - work-items
    - ticket-drafting
---

# Azure DevOps Create Work Item

Turn loose context into a local Azure DevOps work item packet grounded in the official Azure Boards work item model.

Verified against Microsoft Learn pages for About work items and work item types, Scrum workflow in Azure Boards, Agile workflow in Azure Boards, Define, capture, triage, and manage bugs in Azure Boards, and Choose a process on May 9, 2026. Adapted writing guidance was reviewed against the Google developer documentation style guide on August 19, 2026.

## Call-Bluff First

This skill drafts a local packet. It does not create or update a live Azure DevOps work item unless the user separately asks for REST, CLI, or UI automation.

What this skill does well:

- extract the working context and commit to one primary Azure Boards work item type
- create a deterministic folder in the caller's current directory
- produce a copy-pastable `work-item.md` plus supporting artefacts
- default unspecified work to `Product Backlog Item`
- inspect the surrounding repo when run inside a project and surface relevant code snippets
- keep the main draft aligned to the standard field schema, with `Reproduction Steps` added for `Bug`
- keep the writing readable for mixed technical and non-technical audiences
- apply reader-first technical-writing rules without overriding Azure Boards semantics, the packet schema, local terminology, or locale
- shape manual QA sections as targeted, risk-based scenarios that read like a senior tester wrote them
- use official Azure Boards work item primitives instead of invented ticket shapes

## Decision Tree

1. If the user wants a local Azure DevOps-ready draft from notes, chat context, or rough requirements, use this skill.
2. If they want the item created directly in Azure DevOps through the browser, REST API, or Azure CLI, stop and route to an automation or API workflow instead.
3. If they want a standalone Azure DevOps wiki page or general documentation, route to a documentation-writing workflow instead; this skill applies documentation style only inside the local work item packet.
4. If the work item type is missing, draft a `Product Backlog Item`.
5. If the work item type is explicit, use the matching template.
6. If the explicit type is ambiguous, infer it with `references/official-primitives.md`. If the choice is still ambiguous between `Product Backlog Item`, `Feature`, `User Story`, and `Task`, ask one short question.
7. If the current directory is a project or git repository, inspect the codebase before finalizing the draft.
8. If the context is too thin to explain the problem or outcome, ask for missing context before drafting.

## Default Save Path Rule

When the user does not give a destination, create the packet in the current working directory. Do not send it to a hidden cache, temp directory, or home-folder default.

The generated packet layout is:

```text
<current-working-directory>/azure-devops-work-item-<type>-<slug>-<timestamp>/
  work-item.md
  context.md
  sources.md
  metadata.json
```

## Quick Reference

| Task | Command | Why |
| --- | --- | --- |
| Create the default PBI packet in the current directory | `python3 scripts/create_work_item_packet.py --title "Restore team login after token expiry"` | Creates a Product Backlog Item packet beside the command |
| Create a packet from saved notes | `python3 scripts/create_work_item_packet.py --type bug --title "Checkout button freezes on Safari" --context-file ./notes/checkout-bug.md` | Seeds `context.md` from existing notes |
| Save the packet under an explicit directory | `python3 scripts/create_work_item_packet.py --type user-story --title "Resend invite from team page" --save-root ./work-items` | Keeps the packet under a chosen visible folder |
| Check the packet workflow end to end | `python3 scripts/probe_create_work_item_packet.py` | Verifies the scaffold command creates the expected artefacts |
| Confirm type selection and writing rules | Read `references/official-primitives.md` | Keeps the draft aligned to Azure Boards semantics |

## Operating Rules

1. Default to a Scrum `Product Backlog Item` unless the user explicitly asks for a different type or process.
2. Extract the context first. Capture the raw source material in `context.md` even when `work-item.md` becomes more concise.
3. Pick one primary type only: `Product Backlog Item`, `Epic`, `Feature`, `User Story`, `Task`, `Issue`, or `Bug`.
4. Keep `work-item.md` simple. Do not use `#`, `##`, or `###` headings outside a detailed `**Test Scenario**` section. Use bold section labels for the main work item schema.
5. Use this visible schema for non-bug drafts:
   - `**Title**`
   - `**Problem**`
   - `**Action**`
   - `**Outcome**`
   - `**Acceptance Criteria**`
   - `**Developer Notes**`
   - `**Test Scenario**`
6. For `Bug`, add `**Reproduction Steps**` immediately after `**Problem**`. Keep it as simple numbered steps that QA, product, or developers can follow.
7. When producing manual QA content in `**Test Scenario**`, follow the Manual QA Scenario Contract in `references/output-packet.md`: 4-6 targeted scenarios, a `Test environment notes` block, UI-driven steps, observable expected outcomes, behaviour-focused titles, honest `(needs dev support)` staging notes, non-obvious verification traps, and NZ English.
8. Treat the type template as the content contract. The section labels stay consistent; the content inside each section changes for `Product Backlog Item`, `Feature`, `Bug`, `Task`, and other types.
9. Put supporting detail, assumptions, raw notes, and source excerpts in `context.md`, not in the main work item draft.
10. Write for mixed audiences. Prefer plain language, explain the business effect, and keep implementation detail only where it materially changes the request.
11. Apply `references/writing-style.md` to the packet prose. Preserve the fixed Azure section labels and order, project terminology, requested locale, exact literals, and the NZ English Manual QA contract before applying adapted Google style preferences.
12. For security, upgrade, compliance, maintenance, and dependency work, still default to `Product Backlog Item` unless the user asks for `Task`, `Feature`, or another type. Preserve direct title prefixes such as `SECURITY:`, `MAINTENANCE:`, or `COMPLIANCE:` when the source context supports them.
13. When run inside a repository, perform a codebase pass before finalizing `work-item.md`:
   - identify the project structure and likely owning modules with `git status --short`, `rg --files`, package manifests, routing files, service folders, tests, and nearby docs
   - search for domain terms from the work item title, symptoms, UI labels, API names, entities, errors, and likely file names
   - read the smallest relevant files needed to understand the affected path
   - add concise file references and up to 2-4 short snippets in `**Developer Notes**` when they help implementation or triage
   - put longer snippets, investigation notes, and rejected leads in `context.md`
   - do not invent snippets or include unrelated code just to prove investigation happened

## Type Contract

- `Product Backlog Item`: use by default for a user story, requirement, or functional enhancement. Use `templates/product-backlog-item-template.md`.
- `Epic`: use for a larger scenario or initiative that groups multiple features.
- `Feature`: use for a concrete capability with user or business value. Use `templates/feature-template.md`.
- `User Story`: use for who/what/why statements that describe a user need without prescribing implementation. Use `templates/user-story-template.md`.
- `Task`: use for sprint-scale execution work. Use `templates/task-template.md`.
- `Issue`: use for blockers or non-code project issues that could slow or stop delivery. Use `templates/issue-template.md`.
- `Bug`: use for a code defect with reproducible behavior. Use `templates/bug-template.md`; include `Reproduction Steps`.

## Recommended Workflow

1. Read the source context and extract the core problem, audience, and desired outcome.
2. If the caller is inside a repository, inspect the codebase and collect relevant file paths, functions, config, tests, and short snippets.
3. Choose the best-fit work item type with `references/official-primitives.md`.
4. Run `python3 scripts/create_work_item_packet.py --title "<title>"` in the caller's current directory for the default PBI, or add `--type <type>` when the user explicitly names another type. Add `--context-file` when notes already exist on disk.
5. Fill `work-item.md` using the selected template, `references/writing-style.md`, and the packet rules in `references/output-packet.md`, including the Manual QA Scenario Contract when `**Test Scenario**` contains manual QA scenarios.
6. Keep the final file surgical, plain, and ready to paste into Azure DevOps. Do not add extra top-level sections unless the user explicitly asks for them.

## Reading Guide

| Need | Read |
| --- | --- |
| Official Azure Boards type semantics and cross-process notes | `references/official-primitives.md` |
| Mixed-audience field prose, terminology, procedures, links, accessibility, and style precedence | `references/writing-style.md` |
| Packet layout, section-writing rules, Manual QA Scenario Contract, and current-directory behavior | `references/output-packet.md` |
| Failure modes and classification traps | `references/gotchas.md` |
| Product Backlog Item template | `templates/product-backlog-item-template.md` |
| Epic template | `templates/epic-template.md` |
| Feature template | `templates/feature-template.md` |
| User story template | `templates/user-story-template.md` |
| Task template | `templates/task-template.md` |
| Issue template | `templates/issue-template.md` |
| Bug template | `templates/bug-template.md` |

## Gotchas

1. This skill creates a local packet, not a live Azure DevOps item.
2. `Product Backlog Item`, `Feature`, `User Story`, and `Task` are not interchangeable. A PBI is the default Scrum backlog item, a `Feature` groups or frames a deliverable capability, a `User Story` is explicit Agile-process wording, and a `Task` captures execution work.
3. `Bug` means a code defect. If the item is a blocker or dependency without defective behavior, use `Issue` instead.
4. Microsoft documents that Azure DevOps work item types depend on the process. If the user is on Basic, Scrum, or CMMI, confirm the mapping before you draft.
5. The main work item draft should stay light on markup. Use bold section labels and avoid heading syntax.
6. Bugs need a `**Reproduction Steps**` section with simple numbered steps. If the context lacks that detail, ask for it or call out the gap in `context.md`.
7. Do not bury the business impact in engineering detail. Mixed audiences should understand why the item matters after the first short section.
8. Do not invent confidential environment names, URLs, customer names, or system identifiers. Redact or generalize details that are not in the user's supplied context.
9. Code snippets should be evidence, not filler. Include them only when they point to a likely implementation area, defect source, test surface, config dependency, or rollout concern.
10. Do not turn `**Test Scenario**` into an exhaustive permutation table. Manual QA should cover the happy path and the actual risks introduced by the change.
11. Do not use this skill for standalone wiki pages. Its adapted documentation style applies only to the work item packet.
