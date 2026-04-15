# Official Primitives

Use this file to keep type selection grounded in Microsoft Learn rather than in ad hoc ticket habits.

## Source Set

- [About work items and work item types](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/about-work-items?view=azure-devops&tabs=agile-process)
- [Agile workflow in Azure Boards](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/agile-process-workflow?view=azure-devops)
- [Define, capture, triage, and manage bugs in Azure Boards](https://learn.microsoft.com/en-us/azure/devops/boards/backlogs/manage-bugs?view=azure-devops)
- [Choose a process](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/choose-process?view=azure-devops)

## Core Model

Microsoft documents that work item types depend on the selected process. This skill defaults to the Agile process because the most common drafting pattern for mixed-audience software teams maps cleanly to:

- `Epic`
- `Feature`
- `User Story`
- `Task`
- `Issue`
- `Bug`

The official hierarchy is simple:

- `Epic` and `Feature` group work under larger scenarios.
- `User Story` and `Task` track work.
- `Bug` tracks code defects.
- `Issue` tracks nonwork project elements or blockers that can affect delivery.

## Type Selection Guide

| Type | Use it when | Avoid it when |
| --- | --- | --- |
| `Epic` | The item is a larger initiative that will likely break into multiple features or workstreams. | The request is one deliverable capability or one sprint-scale activity. |
| `Feature` | The item describes a concrete capability or slice of value and may group one or more user stories. | The item is really a single user need or a narrow implementation task. |
| `User Story` | The context naturally answers who needs what and why, and the team should not lock into implementation yet. | The work is already purely implementation or operational. |
| `Task` | The work is execution-focused, sprint-scale, and best described as work to do rather than value to deliver. | The item should stay user-facing or business-facing. |
| `Issue` | The item is a blocker, dependency, or project problem rather than defective product behavior. | The item is a reproducible defect in software behavior. |
| `Bug` | The item is a code defect with observed behavior, expected behavior, and enough detail to reproduce it. | The item is a request, enhancement, or delivery blocker without defective behavior. |

## Writing Rules Grounded In The Docs

1. For `User Story`, describe who the feature is for, what users want to accomplish, and why. Do not describe how the feature should be developed.
2. For `Feature`, stay outcome-first. Microsoft positions features as a grouping or delivery level above user stories, so the template should describe the capability and the intended result rather than detailed implementation.
3. For `Task`, think execution and remaining effort. Tasks are where sprint work is broken down.
4. For `Issue`, frame the blocking condition, impact, and next action. Do not blur it into a defect unless the context actually describes defective behavior.
5. For `Bug`, include enough steps to reproduce and the expected behavior. Microsoft explicitly calls out repro steps and acceptance criteria as important bug fields.

## Common Field Signals

These are the most relevant official field concepts behind the templates:

- `Title`: the only field that is always required by default
- `Description`: the main narrative field across work item types
- `Acceptance Criteria`: important for `User Story` and `Bug`
- `Story Points`: relevant for `User Story`
- `Original Estimate` and `Remaining Work`: relevant for `Task`
- `Priority` and `Severity`: especially relevant for `Bug`

The local packet does not force every Azure DevOps field into the Markdown draft. It keeps the draft readable, then preserves source context and references in sidecar files.

## Cross-Process Note

If the user explicitly says the project is not Agile, remap the primary backlog item carefully:

| Agile concept | Basic | Scrum | CMMI |
| --- | --- | --- | --- |
| `Epic` | `Epic` | `Epic` | `Epic` |
| `Feature` | no separate default feature level | `Feature` | `Feature` |
| `User Story` | `Issue` | `Product Backlog Item` | `Requirement` |
| `Issue` blocker | no separate blocker type by default | `Impediment` | `Issue` |
| `Bug` | no native default bug type | `Bug` | `Bug` |

If the project uses Basic, call out that Basic does not ship with a native `Bug` work item type by default. Do not silently draft a Basic bug packet as if it were an Agile bug.
