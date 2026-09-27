# Evaluation scope

`evals.json` contains behavioural scenarios with typed assertions.
`trigger-evals.json` separately contains invocation queries and expected boolean
decisions. Package validation does not execute either set against a model.

For behavioural evaluation, give an isolated agent the skill and one prompt,
without the expected output or assertions. Copy any listed fixtures into its
workspace. Grade the result against the assertions, preserving evidence and
limitations. A comparable baseline receives the same prompt and fixtures
without this skill. Do not grade a specific colour, font, layout, tool sequence,
or prose format unless it is part of that case's contract.

The review and planning cases need no mock application. They can establish
whether the agent distinguishes purposeless decoration from meaningful design,
but cannot certify rendered UI quality. Implementation claims require an
exercised UI and inspected captures. Trigger claims require a functioning
target-harness evaluator with positive and negative health controls.

Report package regressions, model scenario results, visual checks, and trigger
accuracy separately. Authored assertions are not passing model results.

## Exploratory response check

On September 27, 2026 UTC, two isolated participants answered all eight prompts,
one with the skill and one without. Neither received the assertions. Both
preserved meaningful status, explicit branding, and small-edit scope. The
with-skill inventory prompt explicitly excluded gradients, coloured-edge cards,
redundant eyebrows, and fake status; the baseline omitted some exclusions.

The first comparison exposed two over-prescriptive assertions: asking a pure
layout proposal to include a verification plan, and a status critique to recite
motion checks. Those were replaced or removed in favour of observable UI and
truthfulness outcomes. This was one exploratory batch with a refined rubric,
not a held-out benchmark, a measured improvement claim, a rendered application
test, or an automatic-trigger evaluation. Repeat independently before making
stronger behavioural claims.
