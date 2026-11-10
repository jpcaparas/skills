---
name: maintainable-tests
description: "Passive: apply when writing, editing or reviewing automated tests, fixtures, mocks, fakes, regression tests, flaky tests or testability refactors. Tests read as behaviour documentation with isolated side effects and assertions that can fail. Not for throwaway checks."
compatibility: "Optional scanner script needs python3."
---

# Maintainable tests

Passive: apply silently to any test work, and for small edits mention only the decisions that affect the result. Match the repository's framework and style before importing a pattern, and reuse adequate existing coverage instead of duplicating it.

A developer returning in six months should learn the behaviour, its edge cases and why each important test exists from the tests alone.

## Rules

- Name tests after the behaviour and outcome in domain language (`rejects withdrawals that exceed the current balance`), not the function (`returns false from validateInvite`). Parameterised rows get names that say why the row exists.
- Use concrete, domain-shaped values. Keep intent local: no distant factory or hidden global setup needed to understand a test. When readability and DRY conflict, choose readable duplication; extract a helper only when its name keeps domain meaning.
- One behaviour per test, with every assertion needed to prove it (result, state change, emitted event).
- Pick the least powerful double that proves the rule: stub for queries, fake for simple state, spy for an important effect, mock only when the interaction is the behaviour. Mock-heavy tests usually freeze implementation, not behaviour; back adapters with a contract or integration check where they can drift.
- Make tests deterministic: control time, randomness, locale, timezone, concurrency, persistence at clear boundaries.
- Hard-to-test code: use existing safe seams first (framework overrides, scoped and reliably restored patches). Refactor production only when necessary, proportionate and authorised; in tests-only work, propose the change instead of making it. Never expose private internals or widen an interface just to make a test pass. Painful tests are often design feedback.
- Legacy and compatibility behaviour needs a one-line rationale (customer contract, migration, bug reference, or "unknown"). Reuse existing coverage before adding characterisation tests, and change legacy production code in small verified steps.
- A regression test must fail for the bug it guards. Run it against the defect when feasible.
- Review order: tests that can pass while behaviour is broken, then brittle implementation coupling, then missing edge cases, then style.

## Side effects, configuration, compatibility

Make unintended effects fail fast: unstubbed network, real sleeps, destructive commands, writes outside a temp directory, leaked global state. Replace real waiting with a fake clock or scheduler and assert the delay or backoff when it is part of the contract. Cover configurable behaviour as decision dimensions (default, override, effect) plus environment or capability branches only where relevant. Exercise the lowest supported dependency combination and current, plus capability-present and absent paths. Assert the exact artefact (path, type, contents, unchanged-on-cancel). Read `references/side-effects-and-compatibility.md` for an unresolved isolation or compatibility risk.

## Gotchas

- A plausible matcher can prove nothing: a truthiness check on file existence versus its contents, or a correct assertion on the wrong path or type. Trace each assertion back to the observable contract.
- Passing only on the newest dependency does not prove the advertised range.
- Snapshots are not documentation; make sure they expose the semantic difference that matters.
- Coverage numbers distract; check that a test would fail if the behaviour broke.
- Flaky tests destroy trust. Fix the cause (time, order, shared state); do not add retries or sleeps.
- If a pattern here fails or conflicts with the repo's runner, check the installed version and official docs, keep side-effect isolation, say which checks you did not run, and propose a correction rather than adding a brittle test to satisfy this skill.

## Optional scanner

`python3 scripts/analyze_maintainable_tests.py <path> [--json]` flags review prompts (vague names, weak or missing assertions, over-mocking, real sleeps, direct clock and randomness use, missing legacy rationale) across common test layouts. It is a prompt generator, not a verdict: a quiet scan proves nothing and it does not detect network access.
