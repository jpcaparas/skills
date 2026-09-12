# Gotchas

## 1. Product answers need behavior, not wiring

"The checkout button calls `createSession`" is not a product answer. "Clicking checkout sends the customer to hosted payment, then returns them to the dashboard after payment" is.

## 2. UI copy can lie by omission

Copy may say "Cancel anytime", while code gates cancellation by subscription status, permission, region, or plan. Verify the rule, not just the label.

## 3. Tests are intent, runtime code is behavior

Tests are valuable, but they may be stale or narrower than production. Use tests to confirm behavior after tracing the runtime path.

## 4. Feature flags change product truth

If a feature is flag-gated, the right answer often includes rollout state: "available only for flagged accounts" or "controlled by configuration".

## 5. Account state matters

Many product questions hinge on user role, plan, lifecycle state, subscription status, verification state, region, or tenant settings. Find those branches before answering.

## 6. External services can create hidden exceptions

Payments, identity, email, storage, and CRM integrations may fail, retry, or return provider-specific statuses. Explain the product consequence, not the provider mechanics.

## 7. Do not over-share internal paths

Stakeholder answers do not need a long trail of files. Keep evidence compact unless the user asks for a technical appendix.

## 8. "Probably" needs a reason

If the answer is inferred, say what evidence supports it and what would make it certain. Avoid vague hedges without context.

## 9. Broad questions can become architecture tours

Answer the product question first. Only include architecture context if it changes the user-visible behavior or business rule.

## 10. A share-ready answer should not expose private analysis

Do the messy investigation privately. The final answer should not read like a transcript of every search and dead end.
