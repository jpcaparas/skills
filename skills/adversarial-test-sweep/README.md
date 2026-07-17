# adversarial-test-sweep

Installable, language-agnostic skill for running a bounded adversarial campaign over an existing automated test suite.

## Install

```bash
npx skills add jpcaparas/skills --skill adversarial-test-sweep
```

## What it adds

- A recoverable baseline and risk-ledger workflow before test generation
- Systematic attack families for malformed input, boundaries, state, concurrency, dependencies, resources, and harness false positives
- Research-grounded routes for combinatorial, property, fuzz, metamorphic, model-based, differential, mutation, schedule, and fault-injection testing
- Evidence-based test strengthening and pruning without treating coverage or suite size as quality
- Minimal replayable regressions for every confirmed defect
- Explicit budgets, safety boundaries, stopping criteria, and residual-risk reporting

`SKILL.md` is the canonical runbook. The references, templates, evals, validators, and presentation files support that contract without replacing it.
