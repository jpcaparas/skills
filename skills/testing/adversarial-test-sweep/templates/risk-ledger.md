# Adversarial test risk ledger

## Campaign contract

- Target:
- Baseline revision and dirty state:
- Audit-only or authorized changes:
- Supported environments:
- Focused and full-suite commands:
- Case, time, size, sequence, concurrency, memory, output, and shrink budgets:
- Allowed effects and forbidden targets:
- Abort conditions:
- Required repeated-run count and variants:

## Status vocabulary

- `pending` — not yet exercised
- `covered` — passing evidence exists within the declared budget
- `confirmed-defect` — reproducible contract violation found
- `excluded` — intentionally outside scope with a recorded reason
- `escalated` — owned by another test discipline, decision maker, or environment
- `unresolved` — evidence is blocked or contradictory

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
- regression test or corpus location
- repair, owner, or escalation

## Closure check

- Every row is covered, excluded with evidence, escalated, or explicitly unresolved.
- Every confirmed defect has a minimal deterministic regression.
- Every retained test has a distinct contribution.
- Declared verification and repetitions are clean.
- Residual high-risk gaps are visible in the sweep report.
