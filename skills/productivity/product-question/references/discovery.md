# Discovery Workflow

Use this when a product question requires codebase investigation before answering.

## Start With The Product Surface

Turn the question into one or more concrete lookup targets:

- screen, route, page, modal, email, job, notification, or workflow name
- user-facing labels, button text, copy, or empty-state messages
- account state, role, permission, feature flag, plan, region, or tenant condition
- data object names such as invoice, subscription, booking, order, profile, or claim
- test descriptions, fixture names, analytics events, and error messages

Search those terms first. Product questions often hide in copy, tests, route names, config, and feature flag names before they show up in obvious service names.

## Trace The Behavior

Build a small evidence chain:

1. Entry point: where the user action, scheduled process, webhook, or internal event starts.
2. Decision rule: the condition that changes the outcome.
3. State involved: account, role, feature flag, status, setting, date, data record, or external response.
4. User-visible result: what appears, changes, gets blocked, gets sent, or gets saved.
5. Exceptions: edge cases, permissions, missing data, disabled flags, fallbacks, or environment differences.

Stop when you can explain the behavior without naming framework internals.

## Evidence Ranking

Use the strongest available evidence:

| Strength | Evidence |
| --- | --- |
| Strongest | Runtime code path plus tests or fixtures that exercise the same behavior |
| Strong | Runtime code path plus config, route, schema, copy, or docs |
| Medium | Tests, docs, or UI copy without the full runtime path |
| Weak | Naming, nearby code, or inferred ownership without direct behavior proof |

## Confidence Labels

Use confidence only when helpful:

- `High` - direct runtime path found, with tests or config confirming the behavior.
- `Medium` - direct path found, but a branch, environment, feature flag, or external dependency could change the result.
- `Low` - partial evidence only. State what is missing before giving a recommendation.

## Search Tips

- Search exact user-facing words first, then normalized variants.
- Search both product terms and technical synonyms: "cancel", "terminate", "void", "deactivate".
- Check tests for behavior names, then verify against runtime code.
- Check feature flag and permission definitions before assuming a behavior applies to everyone.
- Check environment branches if the answer may differ by production, staging, mobile, or admin mode.

## When To Ask A Question

Ask one concise question only when the product surface is impossible to infer. Good questions name the missing scope:

```text
Which workflow should I trace: the customer checkout flow, the admin refund flow, or the renewal job?
```

Avoid broad process questions before inspecting obvious files.
