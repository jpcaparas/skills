---
name: product-question
description: "Answer product, PM, stakeholder, or non-engineer questions about app behavior by inspecting code and returning a share-ready plain-English answer. Trigger on product question, PM question, stakeholder answer, how a feature works, or why the app behaves that way. Do NOT use for code changes."
compatibility: "Requires repository/file access. rg and git improve discovery; python3 is required for scripts/validate.py and scripts/test_skill.py."
metadata:
  version: "1.0.0"
  short-description: "Answer PM questions from code in share-ready plain English"
  openclaw:
    category: "development"
    subcategory: "code-understanding"
    requires:
      bins: [python3]
    tags: ["product", "pm", "codebase", "explanation", "stakeholders"]
references:
  - discovery
  - answer-contract
  - gotchas
---

# product-question

Turn codebase investigation into a plain-English product answer that can be pasted directly into email, Teams, Slack, or a product doc.

## Decision Tree

What is the user asking?

- A product person, PM, stakeholder, support lead, or non-engineer asks how the app behaves
  Use this skill. Inspect the code, then answer in share-ready product language.

- The user asks "what happens when", "why does the app do X", "how does this feature work", or "what does the user see"
  Use this skill. Trace the real behavior, rules, and exceptions before answering.

- The user wants a response they can forward, paste, or quote
  Use this skill. Make the final response polished enough to share as-is.

- The user asks for implementation details, a fix, a review, or code changes
  Do not stay in this skill unless they also need a product-facing explanation. Switch to the appropriate coding or review workflow.

- The question is broad and the codebase is large
  Ask one concise scope question only if the target feature, screen, customer action, or workflow cannot be inferred.

- The behavior cannot be verified from the available files
  Say what you checked, what remains unknown, and what evidence would settle it. Do not guess.

## Quick Reference

| Situation | Do |
| --- | --- |
| Need to find the behavior | Read `references/discovery.md` |
| Need the final answer shape | Read `references/answer-contract.md` or start from `templates/product-answer.md` |
| Need to avoid common traps | Read `references/gotchas.md` |
| Need a narrow answer fast | Search the user's feature terms, routes, labels, config keys, tests, and user-facing copy |
| Need to answer a broad workflow question | Trace entry point, decision rules, data state, user-visible outcome, and exceptions |
| Need to validate this skill package | Run `python3 scripts/validate.py skills/product-question` |
| Need packaging and eval checks | Run `python3 scripts/test_skill.py skills/product-question` |

## Default Workflow

1. Restate the product question in concrete terms: feature, screen, workflow, user action, account state, or business rule.
2. Search for user-facing terms first: labels, route names, button copy, config names, event names, test names, and docs.
3. Read the files that define actual behavior, not just files with promising names.
4. Trace the path from user action or system event to outcome. Capture inputs, decision rules, state changes, and messages the user can see.
5. Check tests, fixtures, feature flags, permissions, tenant/account conditions, and environment-specific branches for exceptions.
6. Separate observed behavior from inference. Use direct evidence for strong claims.
7. Write the answer for a product reader: outcome first, short paragraphs, minimal jargon, no code unless requested.
8. Add a compact "Confidence" or "Checked" line only when it helps the recipient trust the answer without reading code.

## Share-Ready Answer Standard

The final response should feel like it was written for a product channel, not a developer notebook.

Use this order unless the question needs something different:

1. **Short answer** - one or two sentences that answer the question directly.
2. **What this means for users** - the user-visible behavior, decision, or limitation.
3. **Rules and exceptions** - permissions, feature flags, account states, timing, data conditions, or edge cases that change the answer.
4. **Evidence** - a brief "Checked" line with file or area names, not a code dump.
5. **Confidence** - use only when the evidence is incomplete, inferred, or environment-dependent.

Keep it:

- shareable as-is
- plainspoken
- specific about behavior
- honest about uncertainty
- light on filenames and technical terms
- free of code blocks unless the user explicitly asks for code

## Evidence Rules

Prefer product-relevant evidence over technical inventory:

- Good: "The app only shows the cancellation option after an active subscription is loaded."
- Less useful: "The `SubscriptionActions` component conditionally renders `CancelButton` after `useSubscriptionQuery` returns."

Mention filenames only when they improve trust or make the answer verifiable. Use a short checked line such as:

```text
Checked: subscription settings screen, billing API route, and subscription status tests.
```

If a claim depends on inference, say so:

```text
Confidence: high for the web flow; I did not find mobile-specific handling in the available code.
```

## Tone Contract

- Do not say "I inspected the codebase" as filler. Lead with the answer.
- Do not over-explain frameworks, services, hooks, reducers, migrations, or APIs.
- Replace technical mechanism with product meaning.
- Use short paragraphs over long bullet lists unless the answer naturally needs comparison.
- Make it easy for the user to forward the answer without editing out internal analysis.

## Reading Guide

| Need | Read |
| --- | --- |
| Investigation workflow, search targets, and confidence labels | `references/discovery.md` |
| Share-ready answer structures and examples | `references/answer-contract.md` |
| Common failure modes and recovery patterns | `references/gotchas.md` |
| Copyable final-answer shell | `templates/product-answer.md` |

## Gotchas

1. Do not confuse implementation wiring with product behavior. Product readers usually care about what happens, who sees it, and what changes the result.
2. Do not make the answer sound more certain than the evidence. Product decisions made from a guessed behavior are expensive.
3. Do not dump file paths into the body. Use a short evidence line unless the user asked for technical traceability.
4. Do not answer only from tests or only from UI copy. Tests may describe intended behavior; UI copy may omit hidden rules.
5. Do not bury the answer under process notes. The first sentence should answer the question.
