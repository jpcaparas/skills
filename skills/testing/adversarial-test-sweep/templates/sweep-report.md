# Adversarial test sweep report

Optional format: adapt to the campaign's size and outcome; omit irrelevant fields, not material uncertainty.

## Outcome

- Status: clean within scope / findings remain / blocked / budget exhausted
- Basis: clean requires agreed verification to pass with no unresolved in-scope failures; the other outcomes are honest handoffs, not suite-readiness claims.
- Target and scope:
- Baseline revision and dirty state:
- Authority: audit-only / tests editable / product fixes editable
- Environments and toolchain:
- Execution budgets and abort conditions:

## Baseline

- Focused command, result, duration, skips, retries, and flakes:
- Broader command, result, duration, skips, retries, and flakes:
- Pre-existing failures or environmental blockers:

## Risk ledger summary

| Status | Count | Highest-risk rows or notes |
|---|---:|---|
| Covered |  |  |
| Confirmed defect |  |  |
| Excluded |  |  |
| Escalated |  |  |
| Unresolved |  |  |

## Findings and regressions

For each finding:

- violated contract or invariant
- classification and severity
- minimized reproducer and replay data
- root cause or current diagnosis
- product, test, or harness change
- reproducer; regression test or corpus case for authorized repairs
- prior-failure/pass evidence for repairs, or why that verification remains blocked
- unresolved disposition, next action, or owner when no repair was authorized or completed

## Suite changes

List only tests reviewed or changed in the scoped sweep, not every repository test.

| Test or group | Added / strengthened / consolidated / removed / retained | Distinct behavior or evidence | Comparative removal evidence, when applicable |
|---|---|---|---|
|  |  |  |  |

## Verification evidence

- Commands, variants, repetitions, durations, outcomes, and blocked or unrun checks:
- Coverage scope and interpretation:
- Mutation tool, version, operators, scope, survivors, and dispositions:
- Generated testing tool, version, corpus, distributions, budgets, and saved failures:
- Race, sanitizer, model, schedule, or fault-injection evidence:

## Residual risk and limits

- Unsupported or untested environments:
- Specification gaps:
- Techniques not run and why:
- Excluded resource, production, performance, chaos, or security work:
- Remaining flakes, unresolved findings, or high-risk ledger rows:
- Claims this sweep does not establish:
