---
name: mockable-code
description: "Passive coding-quality skill for mockable, stubbable, test-double-friendly code. Use whenever writing, editing, refactoring, reviewing, or planning code that touches dependencies, I/O, time, randomness, external services, configuration, or tests. Do NOT use for non-code writing, one-off shell commands, or deliberately throwaway prototypes."
compatibility: "No external dependencies. Optional helper scripts require python3."
metadata:
  version: "1.0.0"
  short-description: "Prefer code that can be mocked, stubbed, and tested"
  openclaw:
    category: "development"
    requires:
      bins: [python3]
references:
  - principles
  - boundaries
  - test-doubles
  - review-rubric
  - gotchas
  - source-notes
---

# mockable-code

Write, edit, refactor, and review code so dependencies can be replaced by mocks, stubs, fakes, or in-memory implementations without distorting production design.

## Passive Trigger

Load this skill in the background whenever the task involves source code and any behavior depends on collaborators, I/O, time, randomness, persistence, configuration, network calls, queues, SDKs, process state, or framework context. Keep it lightweight for tiny edits: apply the core rules silently, then mention only the mockability decisions that affect the final implementation.

## Decision Tree

What are you doing?

- Adding code that calls a dependency:
  Accept the dependency from the caller when practical. Keep domain policy separate from construction, configuration, and transport.

- Refactoring hard-to-test code:
  Read `references/boundaries.md`. Move side effects behind the smallest useful boundary before changing behavior.

- Choosing a test double:
  Read `references/test-doubles.md`. Prefer the least powerful double that proves the behavior: stub for canned answers, fake for realistic in-memory behavior, mock or spy for interaction contracts.

- Reviewing code:
  Use `references/review-rubric.md`. Lead with hidden side effects, hardcoded collaborators, brittle interaction tests, and missing contract coverage.

- Planning work for another agent or teammate:
  Include the dependency boundaries, which doubles to use, verification commands, and stop conditions. Avoid vague advice like "make it injectable" without naming the dependency and owner.

- The user asks for maximum speed or a throwaway prototype:
  Keep production code simple, but still isolate expensive or irreversible effects when the cost is low. Do not build broad abstractions only for hypothetical future tests.

## Quick Reference

| Situation | Default action |
|---|---|
| Direct network, database, file, clock, random, env, or queue access | Keep it at an outer boundary or pass it in behind a small contract |
| Business rule mixed with an SDK call | Extract the rule into a deterministic function and inject the SDK-facing adapter |
| Constructor creates clients internally | Accept the client, factory, or configuration from the caller unless local patterns say otherwise |
| Static/global singleton dependency | Prefer an explicit collaborator, context object, or narrow wrapper at the boundary |
| Framework handler | Keep parsing and response formatting in the handler; move policy into callable services/functions |
| Tests need real external services | Use a fake, stub, contract test, or local test container before hitting shared infrastructure |
| Interface seems useful | Add it only when there is real substitution, a boundary to protect, or a language convention requiring it |
| Review finds unmockable code | Cite the hidden dependency and show the smallest repair path, not a blanket rewrite |

## Core Rules

1. Separate decisions from effects. Domain policy should be testable without real networks, clocks, files, databases, queues, or randomness.
2. Make collaborators explicit at module, constructor, function, handler, or context boundaries.
3. Prefer narrow contracts that describe what the caller needs, not everything the dependency can do.
4. Keep default production wiring convenient, but let tests override collaborators without monkeypatching global state.
5. Use fakes for stateful behavior, stubs for fixed responses, mocks/spies for important interactions, and contract tests for adapters.
6. Avoid exposing private internals just so tests can reach them. Move behavior to a better-named unit instead.
7. Do not add abstractions with only imaginary substitutes. Simple code with one clear replacement point beats layers of unused interfaces.
8. Preserve local style, framework conventions, and existing test infrastructure before introducing a new testing pattern.

## Mockability Gate

Before finishing code changes, run this gate mentally and with local tooling where available:

| Gate | Pass condition |
|---|---|
| Dependency ownership | A reader can tell who creates each external dependency and who consumes it |
| Substitution | Tests can replace slow, flaky, costly, or irreversible collaborators without changing production code |
| Determinism | Time, randomness, and process/environment reads are controlled at a boundary |
| Contract size | Interfaces or protocols contain only the operations the caller actually needs |
| Production wiring | The normal runtime path remains straightforward and easy to trace |
| Test intent | Tests assert behavior and important contracts, not incidental call order |
| Failure modes | Error paths from dependencies can be simulated without causing real side effects |
| Scope | The change improves testability without unrelated rewrites or framework churn |

## Operating Workflow

1. Recon first.
   Read nearby construction, dependency injection, test fixture, mocking, and adapter patterns before designing the change.

2. Identify hard dependencies.
   List real I/O, time, randomness, config, SDK, database, framework, and global state touches. Decide which ones should stay at the boundary.

3. Pick the smallest substitution point.
   Use the codebase's normal mechanism: constructor parameter, function parameter, interface/protocol, factory, context object, module import override, fixture, or framework provider.

4. Implement without test-only contortions.
   Keep production names honest. Do not add setters, public mutable fields, or broad service locators solely for tests.

5. Verify with meaningful doubles.
   Add focused tests that replace dependencies, cover failure paths, and keep at least one adapter or integration test where the boundary could drift.

6. Report plainly.
   Name the dependency boundaries changed, the doubles or fixtures used, commands run, and any remaining real-service risk.

## Optional Helper

Use the helper as a fast review prompt scanner, not as a verdict:

```bash
python3 scripts/analyze_mockability.py /path/to/project
python3 scripts/analyze_mockability.py /path/to/project --json
```

It flags likely hardcoded effects and globals so a human or agent can inspect them. A quiet scan does not prove code is mockable, and a noisy scan does not prove code is wrong.

## Reading Guide

| Need | Read |
|---|---|
| Principles behind the defaults | `references/principles.md` |
| Isolating dependencies and side effects | `references/boundaries.md` |
| Choosing mocks, stubs, fakes, spies, and contract tests | `references/test-doubles.md` |
| Review findings and severity ordering | `references/review-rubric.md` |
| Common traps and anti-patterns | `references/gotchas.md` |
| Source influence and adaptation notes | `references/source-notes.md` |

## Gotchas

1. Mockable code is not the same as mock-heavy tests. Prefer behavior tests and fakes when they reduce brittleness.
2. Interfaces for every class make code harder to navigate. Add contracts where substitution or ownership boundaries are real.
3. Hidden reads from clocks, random generators, environment variables, and global context often break tests as much as network calls do.
4. Monkeypatching can be useful, but it should not be the only way to replace a collaborator in core production code.
5. Dependency injection can hide construction errors if production wiring has no integration or contract coverage.
6. Do not make private methods public for tests. Extract a real policy unit or test through observable behavior.
