# Work item types and processes

Sources, checked against Microsoft Learn on 2026-05-09 and the About work items page re-read on 2026-11-10 (default types per process unchanged): [About work items and work item types](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/about-work-items?view=azure-devops&tabs=agile-process), [Scrum workflow](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/scrum-process-workflow?view=azure-devops), [Agile workflow](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/agile-process-workflow?view=azure-devops), [manage bugs](https://learn.microsoft.com/en-us/azure/devops/boards/backlogs/manage-bugs?view=azure-devops), [choose a process](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/choose-process?view=azure-devops).

## By process

| Backlog concept | Basic | Agile | Scrum | CMMI |
| --- | --- | --- | --- | --- |
| Epic | Epic | Epic | Epic | Epic |
| Feature | none by default | Feature | Feature | Feature |
| Primary backlog item | Issue | User Story | Product Backlog Item | Requirement |
| Blocker | none by default | Issue | Impediment | Issue |
| Bug | none by default | Bug | Bug | Bug |

Custom processes vary; use the types the project actually has. For a type with no template of its own (`Requirement`, `Impediment`, custom), say so and agree a local adaptation of the nearest shape rather than presenting it as process-native.

## Choosing a type

- `Epic`: a larger initiative that will split into several features.
- `Feature`: a concrete capability with user or business value that may group stories or PBIs. Outcome-first.
- `Product Backlog Item` / `User Story`: a customer or product need. A story says who needs what and why, without prescribing how.
- `Task`: sprint-scale execution work with remaining effort; not user-facing value.
- `Issue`: a blocker, dependency or project problem that could slow delivery. Frame the condition, the impact and the next action.
- `Bug`: defective software behaviour with observed versus expected behaviour and enough detail to reproduce.

Field signals: `Title` is the only always-required field; `Acceptance Criteria` matters for backlog items and bugs; `Story Points` for User Story; `Original Estimate` and `Remaining Work` for Task; `Priority` and `Severity` for Bug. The draft does not need every field.
