# Gotchas

1. This skill is for drafting a local packet, not for creating the work item in Azure DevOps itself.
2. Do not confuse a blocker with a defect. `Issue` is for delivery blockers or nonwork problems. `Bug` is for defective software behavior.
3. Do not collapse `Product Backlog Item`, `Feature`, `User Story`, and `Task` into one generic ticket shape. Default to PBI only when the user has not specified another type.
4. The packet should be easy to paste into Azure DevOps and easy to read in chat or email. Use bold section labels, but avoid heading syntax and heavy Markdown.
5. If the context is mostly implementation detail but the title is user-facing, pause and decide whether the item is really a `Task` under a larger `Feature` or `User Story`.
6. When the project uses Basic, do not assume a native `Bug` work item exists. Confirm the process or suggest a process-appropriate type.
7. Bugs without reproducible steps become low-trust tickets quickly. Put simple numbered steps in `**Reproduction Steps**`, keep post-fix validation in `**Test Scenario**`, capture missing detail in `context.md`, and call out the gap if necessary.
8. Avoid overfilling the main draft. If a sentence only helps engineers during implementation, it usually belongs in `context.md`.
9. Do not add `Requirements/Solution` or other extra top-level sections unless the user explicitly requests that shape. Use `**Action**`, `**Developer Notes**`, and `**Test Scenario**` instead. `**Reproduction Steps**` is the one intentional bug-only exception.
10. When source notes mention sensitive hostnames, environments, customers, or incident details, redact or generalize them in examples and keep only the detail needed to draft the work item.
