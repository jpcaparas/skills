---
name: azure-devops-create-work-item
description: "Draft a local Azure DevOps work item packet from loose context using official Azure Boards work item primitives, then save it in the caller's current directory as a folder with `work-item.md`, `context.md`, `sources.md`, and `metadata.json`. Use when asked to create an Azure DevOps work item, feature ticket, bug report, user story, task, issue, or epic from notes, chats, requirements, or defect reports, especially when the output should be surgical, copy-pastable, and readable by both technical and non-technical audiences. Trigger on: 'create an Azure DevOps work item', 'turn this into a feature ticket', 'draft a bug work item', 'make an ADO user story', 'create a work item folder'. Do NOT use for live Azure DevOps REST or CLI creation, bulk migration, wiki authoring, or project status reporting."
compatibility: "Requires: python3. Optional network access only when re-checking Microsoft Learn documentation."
metadata:
  version: "1.0.0"
  repo_tags:
    - azure-devops
    - work-items
    - ticket-drafting
---

# Azure DevOps Create Work Item

Turn loose context into a local Azure DevOps work item packet grounded in the official Azure Boards work item model.

Verified against Microsoft Learn pages for About work items and work item types, Agile workflow in Azure Boards, Define, capture, triage, and manage bugs in Azure Boards, and Choose a process on April 15, 2026.

## Call-Bluff First

This skill drafts a local packet. It does not create or update a live Azure DevOps work item unless the user separately asks for REST, CLI, or UI automation.

What this skill does well:

- extract the working context and commit to one primary Agile work item type
- create a deterministic folder in the caller's current directory
- produce a copy-pastable `work-item.md` plus supporting artefacts
- keep the writing readable for mixed technical and non-technical audiences
- use official Azure Boards work item primitives instead of invented ticket shapes

## Decision Tree

1. If the user wants a local Azure DevOps-ready draft from notes, chat context, or rough requirements, use this skill.
2. If they want the item created directly in Azure DevOps through the browser, REST API, or Azure CLI, stop and route to an automation or API workflow instead.
3. If the work item type is explicit, use the matching template.
4. If the type is missing, infer it with `references/official-primitives.md`. If the choice is still ambiguous between `Feature`, `User Story`, and `Task`, ask one short question.
5. If the context is too thin to explain the problem or outcome, ask for missing context before drafting.

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
| Create a feature packet in the current directory | `python3 scripts/create_work_item_packet.py --type feature --title "Restore team login after token expiry"` | Creates the default packet folder beside the command |
| Create a packet from saved notes | `python3 scripts/create_work_item_packet.py --type bug --title "Checkout button freezes on Safari" --context-file ./notes/checkout-bug.md` | Seeds `context.md` from existing notes |
| Save the packet under an explicit directory | `python3 scripts/create_work_item_packet.py --type user-story --title "Resend invite from team page" --save-root ./work-items` | Keeps the packet under a chosen visible folder |
| Check the packet workflow end to end | `python3 scripts/probe_create_work_item_packet.py` | Verifies the scaffold command creates the expected artefacts |
| Confirm type selection and writing rules | Read `references/official-primitives.md` | Keeps the draft aligned to Azure Boards semantics |

## Operating Rules

1. Default to the Agile process unless the user explicitly says their project uses Basic, Scrum, or CMMI.
2. Extract the context first. Capture the raw source material in `context.md` even when `work-item.md` becomes more concise.
3. Pick one primary type only: `Epic`, `Feature`, `User Story`, `Task`, `Issue`, or `Bug`.
4. Keep `work-item.md` simple. Do not use `#`, `##`, or `###` headings. Use bold section labels such as `**Problem**` and ordinary paragraphs, bullets, and numbered lists.
5. Write for mixed audiences. Prefer plain language, explain the business effect, and keep implementation detail only where it materially changes the request.
6. Use the type template as the contract. `Feature` and `Bug` are strict; the other types should stay close to their templates unless the context forces a small adjustment.
7. Put supporting detail, assumptions, raw notes, and source excerpts in `context.md`, not in the main work item draft.

## Type Contract

- `Epic`: use for a larger scenario or initiative that groups multiple features.
- `Feature`: use for a concrete capability with user or business value. Use `templates/feature-template.md`.
- `User Story`: use for who/what/why statements that describe a user need without prescribing implementation. Use `templates/user-story-template.md`.
- `Task`: use for sprint-scale execution work. Use `templates/task-template.md`.
- `Issue`: use for blockers or non-code project issues that could slow or stop delivery. Use `templates/issue-template.md`.
- `Bug`: use for a code defect with reproducible behavior. Use `templates/bug-template.md`.

## Recommended Workflow

1. Read the source context and extract the core problem, audience, and desired outcome.
2. Choose the best-fit work item type with `references/official-primitives.md`.
3. Run `python3 scripts/create_work_item_packet.py --type <type> --title "<title>"` in the caller's current directory, adding `--context-file` when notes already exist on disk.
4. Fill `work-item.md` using the selected template and the writing rules in `references/output-packet.md`.
5. Keep the final file surgical, plain, and ready to paste into Azure DevOps.

## Reading Guide

| Need | Read |
| --- | --- |
| Official Azure Boards type semantics and cross-process notes | `references/official-primitives.md` |
| Packet layout, section-writing rules, and current-directory behavior | `references/output-packet.md` |
| Failure modes and classification traps | `references/gotchas.md` |
| Epic template | `templates/epic-template.md` |
| Feature template | `templates/feature-template.md` |
| User story template | `templates/user-story-template.md` |
| Task template | `templates/task-template.md` |
| Issue template | `templates/issue-template.md` |
| Bug template | `templates/bug-template.md` |

## Gotchas

1. This skill creates a local packet, not a live Azure DevOps item.
2. `Feature`, `User Story`, and `Task` are not interchangeable. A `User Story` expresses a user need, a `Feature` groups or frames a deliverable capability, and a `Task` captures execution work.
3. `Bug` means a code defect. If the item is a blocker or dependency without defective behavior, use `Issue` instead.
4. Microsoft documents that Azure DevOps work item types depend on the process. If the user is on Basic, Scrum, or CMMI, confirm the mapping before you draft.
5. The main work item draft should stay light on markup. Use bold section labels only and avoid heading syntax.
6. Bugs need reproducible steps and expected behavior. If the context lacks that detail, ask for it or call out the gap in `context.md`.
7. Do not bury the business impact in engineering detail. Mixed audiences should understand why the item matters after the first short section.
