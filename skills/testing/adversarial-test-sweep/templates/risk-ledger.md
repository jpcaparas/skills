# Adversarial test risk ledger

Optional format: keep only fields relevant to this campaign. Follow the outcome and safety rules in `SKILL.md`, not a requirement to fill every field.

## Campaign contract

- Target:
- Baseline revision and dirty state:
- Audit-only or authorized changes:
- Supported environments:
- Focused and full-suite commands:
- Stopping budget and method-specific limits needed to bound risk:
- Allowed effects and forbidden targets:
- Abort conditions:
- Repetitions and variants, when justified:

## Status vocabulary

- `pending` — not yet exercised
- `covered` — passing evidence exists within the declared budget
- `confirmed-defect` — reproducible contract violation found
- `excluded` — intentionally outside scope with a recorded reason
- `escalated` — owned by another test discipline, decision maker, or environment
- `unresolved` — evidence is blocked, contradictory, or not reached before the budget ended

## Risk rows

| ID | Contract or invariant | Source and consequence | Adversarial hypothesis or transformation | Oracle | Current evidence or gap | Technique and budget | Priority | Status and disposition |
|---|---|---|---|---|---|---|---|---|
| R-001 |  |  |  |  |  |  |  | pending |

## Findings and replay packets

For every failing row, record:

- finding classification: product, test, harness/environment, specification gap, or flake
- minimized concrete input, sequence, schedule, or fault set
- expected and observed behavior
- toolchain, versions, environment, and configuration
- seed plus generator version, when applicable
- event or schedule trace, when applicable
- reproducer location; regression test or corpus location for authorized repairs
- repair, owner, or escalation

## Closure check

- Every row is covered, a documented confirmed defect, excluded with evidence, escalated, or explicitly unresolved.
- Every authorized repair has a durable regression, with prior-failure/pass evidence or an explicit verification limit; audit-only findings remain documented without code changes.
- Every retained test reviewed or changed in this sweep has a distinct contribution; untouched tests are outside that claim.
- Verification outcomes and unrun checks are recorded. Claim clean only when agreed verification passes and no in-scope failure remains; findings, blocked work, or an exhausted budget are valid non-clean handoffs.
- Residual high-risk gaps are visible in the sweep report.
