# Gotchas

1. This skill is for drafting a local packet, not for creating the work item in Azure DevOps itself.
2. Do not confuse a blocker with a defect. `Issue` is for delivery blockers or nonwork problems. `Bug` is for defective software behavior.
3. Do not collapse `Feature`, `User Story`, and `Task` into one generic ticket shape. The Agile docs use those types for different levels of planning.
4. The packet should be easy to paste into Azure DevOps and easy to read in chat or email. Heavy Markdown works against that goal.
5. If the context is mostly implementation detail but the title is user-facing, pause and decide whether the item is really a `Task` under a larger `Feature` or `User Story`.
6. When the project uses Basic, do not assume a native `Bug` work item exists. Confirm the process or suggest a process-appropriate type.
7. Bugs without reproducible steps become low-trust tickets quickly. Capture the missing detail in `context.md` and call out the gap if necessary.
8. Avoid overfilling the main draft. If a sentence only helps engineers during implementation, it usually belongs in `context.md`.
