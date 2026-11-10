---
name: product-question
description: "Answers product, PM, stakeholder or support questions about how an app behaves by tracing the code, then writes a share-ready plain-English answer. Use for 'how does X work' or 'why does the app do Y'. Not for code changes or reviews."
---

# Product question

Investigate like an engineer, answer like a product partner. The investigation stays private; the reply should be forwardable as written.

## Investigating

- Start from the owning files if the user named them. Otherwise search the user-facing words: labels, button copy, route names, config and flag names, event names, test descriptions, error messages, plus synonyms ("cancel", "terminate", "void").
- Read the code that defines the behaviour, not files that merely sound relevant. Trace trigger → decision rule → state involved → what the user sees, then look for exceptions: roles, plans, account or tenant state, feature flags, environment or platform branches (web vs mobile, staging vs production), missing-data fallbacks.
- Tests show intent and can be stale or narrower than production; UI copy can omit hidden rules ("Cancel anytime" over a status-gated action). Confirm one against the other and against the runtime path.
- Code shows what this checkout does, not what a deployment or external service does today. Say so when it matters.
- Ask one short scope question only when the feature or workflow cannot be inferred; otherwise inspect first.
- If the behaviour cannot be verified from the available files, say what you checked, what is unknown and what evidence would settle it. Do not guess.

## Answering

- First sentence answers the question. No "I inspected the codebase".
- Describe behaviour, not wiring: "clicking checkout sends the customer to hosted payment and back to the dashboard", not "the button calls `createSession`". Say "the app", not "the code".
- Give the conditions that change the answer (role, plan, flag, state, platform) and what the user sees in each.
- Keep technical detail to what helps or was asked for, with its product meaning. If the user wants exact statuses or code, give them.
- Add a brief "Checked:" line (areas, screens, tests, config) so the reader can trust it, not a file dump.
- Add a confidence note only when evidence is incomplete, inferred or environment-dependent, and say what would make it certain, e.g. "high for the web flow; no mobile-specific code in this repo".
- Short paragraphs over long bullet lists unless comparing states.
