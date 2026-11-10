---
name: azure-devops-create-work-item
description: "Drafts Azure DevOps work items (PBI, User Story, Bug, Task, Feature, Epic, Issue) as local, paste-ready packets from loose notes or a repo, with manual QA scenarios. Not for live REST/CLI creation, wiki pages or status reporting."
---

# Azure DevOps work item packets

Output is a local draft, never a live work item. Create or update one in Azure DevOps only if the user separately asks for it.

## Packet

Unless the user names a destination, create `azure-devops-work-item-<type>-<slug>-<timestamp>/` in the current directory (not a temp or cache directory) containing:

- `work-item.md`: the paste-ready draft.
- `context.md`: raw notes, assumptions, missing details, long logs, longer snippets, and under `**Codebase investigation**` the searched paths and dead ends. Anything that only helps an engineer mid-implementation goes here, not in the draft.

## Type

Use the type the user gave. Otherwise use the project's process (supplied, or observed in repo or exports): Agile → `User Story`, Scrum → `Product Backlog Item`, CMMI → `Requirement`, Basic → `Issue`. Only when neither type nor process is known, fall back to Scrum `Product Backlog Item`. If an explicit type conflicts with the known process, say so rather than silently remapping. Security, upgrade, compliance and dependency work follows the same rule, not an automatic `Task`; keep prefixes like `SECURITY:` or `MAINTENANCE:` when the source supports them. Ask a question only when the remaining uncertainty would change the packet.

Read `references/work-item-types.md` when the choice between types, or between processes, is unclear.

## Draft schema

This is the owner's house shape. Keep these bold labels (not `#` headings) in this order unless the user asks for another shape; adapt wording and detail freely inside them:

```
**Title**
**Problem**
**Action**
**Outcome**
**Acceptance Criteria**
**Developer Notes**
**Test Scenario**
```

For a `Bug`, add `**Reproduction Steps**` straight after `**Problem**`: numbered, simple, preconditions first, ending in the observed wrong result. If the source lacks the detail, ask or record the gap in `context.md`; do not invent steps.

Field intent:

- **Title:** specific sentence-case name for the change, defect or outcome.
- **Problem:** the affected role or component and the supported impact, readable by technical and non-technical people without codebase trivia. Separate observation from suspected cause, and keep proposed solutions out.
- **Action:** the smallest useful delivery path, not a file-by-file diary. Tasks stay execution-focused; user stories say who, what and why without prescribing implementation.
- **Outcome:** what becomes observably true when it is done.
- **Acceptance Criteria:** observable and testable, one behaviour per line, `must` for requirements and `can` for capabilities, never `should` where pass/fail matters. Include failure, empty or permission states when they define done.
- **Developer Notes:** constraints, dependencies, rollout notes, open questions and concise code references.
- **Test Scenario:** QA-facing validation; for manual QA read `references/manual-qa.md`.

Every acceptance criterion, edge case and verification surface must come from the supplied context, repo evidence or an explicit user decision. Do not infer an eligibility rule, cutoff, owner, state transition or dashboard from suggestive wording; record the ambiguity or ask. Do not invent confidential environment names, URLs, customers or identifiers; generalise or redact them. Preserve exact literals, UI labels and supported prefixes. Use unambiguous dates with a time zone when timing matters.

## Repository pass

When run inside a repository, look at the code before finalising: find the owning modules, tests and config by searching for terms from the title, symptoms, UI labels and API names, and read the smallest set of files that explains the affected path. Put concise file references and only the short snippets that point at the likely defect source, test surface, config or rollout concern in Developer Notes; zero is fine. Never add code to prove you looked.

## Gotchas

- `Bug` is a code defect. A blocker or dependency with no defective behaviour is an `Issue`.
- Basic ships without a native `Bug` type; flag that rather than drafting an Agile-shaped bug.
- A title that sounds user-facing over implementation-only content may really be a `Task` under a Feature or Story.
- Keep the business impact in the first short section; do not bury it in engineering detail.
- Locale: NZ English by default (behaviour, authorised, enrolment) unless the user or project specifies another; exact UI labels and literals are never respelled.
