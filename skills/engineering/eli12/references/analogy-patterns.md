# Analogy Patterns

Use analogies to orient the reader, not to replace the system.

## Analogy checklist

Before using an analogy, verify all three:

1. It matches the actual job of the code.
2. It clarifies the most important behavior.
3. It can be tied back to exact files or symbols right away.

If any of those fail, skip the analogy.

## Good analogy shapes

| Code concept | Everyday analogy | Why it works |
| --- | --- | --- |
| Router | front desk or traffic cop | it sends each request to the right place |
| Middleware | security checkpoint | it inspects requests before they continue |
| Queue | ticket line | work waits its turn instead of happening immediately |
| Cache | sticky note or nearby shelf | it keeps recently needed information close |
| Event bus | group announcement board | one thing publishes news and multiple listeners react |
| State machine | board game rules | the next move depends on the current state |
| Worker / background job | kitchen prep station | work happens off to the side so the main flow stays fast |
| Repository / data access layer | filing clerk | it knows how to fetch and store records |
| Controller | receptionist | it receives the request and hands work to the right internal helper |
| Orchestrator service | conductor | it coordinates multiple parts without necessarily doing the raw work itself |

## Good analogy example

The retry queue is like a call-back list at a busy repair shop: failed jobs do not disappear, they get put back in line for another attempt later. In this codebase, that maps to the background worker that re-enqueues failed tasks with a delay.

## Bad analogy example

"The backend is the brain" is too vague. It does not tell the reader which part decides, stores, routes, or executes.

## Rules for analogy discipline

- One concept, one analogy.
- Do not stack multiple metaphors in the same paragraph.
- Prefer everyday systems with clear jobs: front desk, warehouse shelf, checklist, assembly line, ticket line.
- Avoid fantasy metaphors, sports metaphors, and anthropomorphic phrasing.
- If the code has an important mismatch with the analogy, name the mismatch.

## When not to use analogies

- low-level algorithm details where exact steps matter more than intuition
- security-sensitive behavior where oversimplification hides a real constraint
- concurrency explanations where the analogy erases race conditions or timing
- already-simple code that is easier to explain directly
