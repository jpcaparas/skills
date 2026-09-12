---
name: adversarial-test-sweep
description: "Run a bounded adversarial sweep of an existing test suite. Use to harden a suite or subsystem against malformed inputs, boundaries, invalid state, races, dependency/resource failures, weak or redundant tests, flakes, and missing durable regressions. Skip ordinary test additions, load, chaos, and penetration testing."
compatibility: "Core guidance is language- and framework-agnostic. Execution uses the target project's own test tooling; optional package checks require Python 3.10+."
metadata:
  version: "1.0.0"
references:
  - adversarial-techniques
  - suite-evidence
---

# Adversarial test sweep

Audit and harden an existing automated test suite as a finite, evidence-led campaign. Try to falsify the product's contracts, expose tests that can pass while behavior is broken, repair confirmed defects, preserve each failure as a deterministic regression, and remove only tests proven to add no distinct protection.

This skill is deliberately language-agnostic. Detect and use the repository's languages, frameworks, commands, conventions, and supported environments rather than importing a preferred stack.

## Route the request

Use this skill when the user asks for one or more of these outcomes:

- a comprehensive or adversarial audit of an existing test suite
- a focused hardening sweep over a risky component, incident area, or subsystem
- systematic edge, invalid-state, concurrency, dependency-failure, or resource-boundary testing
- an evidence-based review of weak, flaky, redundant, or false-positive tests
- a regression campaign that turns discovered defects into durable protection

Use ordinary test guidance instead for routine tests around one feature or a single known fix. If available, load the installed `maintainable-tests` skill when writing or editing individual tests; it is a soft companion, while this skill owns the campaign, risk ledger, adversarial discovery loop, and completion gate.

Route production load or endurance work to performance testing, deployed fault campaigns to chaos engineering, and exploit-seeking work to security testing. This skill may simulate resource and dependency failures locally, but it does not authorize stress against shared systems, production mutation, destructive effects, or penetration testing.

## Non-negotiable evidence rules

1. Define a finite scope and budget before generating cases. “Try everything” is not a reproducible test plan.
2. Derive attacks from contracts, invariants, state transitions, call sites, schemas, historical defects, dependency behavior, and operational risks. Do not dump a generic edge-case list into the suite.
3. Give every test a distinct job: distinguish an observable contract, cover a credible risk partition, kill a meaningful fault, or preserve a confirmed regression.
4. Separate reachability from observation. Executing a line does not prove that a test would notice its behavior changing.
5. Use coverage, mutation, generated-case counts, and repetition as evidence, never as standalone quality targets.
6. Treat every failure as unclassified until evidence distinguishes a product defect, test defect, environmental failure, unsupported assumption, or flaky outcome.
7. Never make a suite green by weakening a correct oracle, adding arbitrary retries or sleeps, catching broader errors, skipping unexplained failures, or deleting the only reproducer.
8. State the remaining uncertainty. A bounded clean sweep reduces known risk; it does not prove correctness, race freedom, leak freedom, or exhaustive coverage.

## Operating workflow

### 1. Establish the campaign contract

Inspect repository guidance, production code, nearby tests, fixtures, test helpers, configured commands, supported versions, and current working-tree state. Record:

- target components, entry points, contracts, and test levels
- audit-only versus authorized test and product-code changes
- supported runtime, platform, dependency, locale, and configuration matrix
- allowed local or sandbox effects and forbidden remote or destructive effects
- wall-clock, case-count, input-size, sequence-length, concurrency, memory, output, and shrink budgets
- which optional analyzers are installed: coverage, mutation, race, sanitizer, fuzz, model, or property tooling
- the required verification breadth and repeated-run count

Use proportional budgets. Keep resource exhaustion simulated or safely capped, use synthetic or approved data, and isolate file, network, process, clock, random, scheduler, and persistent-state effects. Obtain separate authority before any costly shared-environment or production experiment.

**Complete when:** scope, authority, environments, budgets, test commands, and abort conditions are explicit enough that the sweep cannot silently expand.

### 2. Preserve and measure the baseline

Record the exact revision, dirty working-tree state, toolchain identity, environment, focused command, and full-suite command. Run the narrowest relevant suite, then the broader configured suite when affordable. Capture outcomes, durations, skips, retries, leaks, hangs, and known flakes without editing them away.

Map current tests to observable behaviors or invariants. Mark pre-existing failures and environmental blockers separately. If improvement work already started, recover the old state from version control or another immutable baseline before claiming a comparison.

**Complete when:** the original code and suite are recoverable, every baseline failure is classified or explicitly unresolved, and later changes can be compared with like-for-like commands and environments.

### 3. Build a risk ledger

Copy `templates/risk-ledger.md` when a persistent artifact helps. Add one row per behaviorally distinct risk:

- contract, invariant, state transition, or non-effect that must hold
- source of truth and consequence if it fails
- adversarial transformation or fault hypothesis
- oracle: what independently observable result would distinguish correct from broken behavior
- current evidence and the gap, if any
- priority, budget, status, and final disposition

Seed the ledger from repository evidence, then cover only applicable families:

| Risk family | Questions to attack |
|---|---|
| Inputs and representation | What happens at empty, missing, malformed, just-inside, just-outside, extreme, duplicate, reordered, encoded, normalized, or valid-but-surprising values? |
| State and sequence | Are initial, terminal, repeated, forbidden, partial, rolled-back, serialized, restored, cached, and corrupted states handled without violating invariants? |
| Dependencies and errors | What if a dependency rejects, times out, cancels, delays, truncates, duplicates, reorders, corrupts, or partially succeeds? Are cleanup and non-effects preserved? |
| Time and concurrency | Can first use, double completion, cancellation, retry, stale reads, visibility, or interleavings lose work, duplicate effects, deadlock, livelock, or starve progress? |
| Resources and lifecycle | Do caps, backpressure, acquisition failure, partial allocation, cleanup failure, oversized safe inputs, and repeated use preserve accounting and release resources? |
| Configuration and composition | Do option interactions, version capabilities, locale/time-zone rules, equivalent representations, and composed operations obey the same contract? |
| Test harness | Can shared fixtures, order, wall time, randomness, network, environment, broad matchers, or wrong assertion subjects let a broken behavior pass? |

Prioritize by consequence, change frequency, historical defects, complexity, weak observability, and uncertainty. A low-value Cartesian product is not thoroughness.

**Complete when:** every in-scope behavior and credible failure family is represented, explicitly excluded with a reason, or escalated to the appropriate test discipline.

### 4. Select the smallest powerful technique

Start with direct examples and boundary partitions. Escalate only when another technique reaches risks that examples cannot cover economically.

| Need | Prefer |
|---|---|
| Discrete input or rule boundaries | Equivalence partitions, boundary values, decision tables, or constrained combinatorial cases |
| Laws over many values | Property-based generation with measured distributions and shrinking |
| Robustness across broad inputs | Coverage-guided or structured fuzzing with crash, hang, resource, and invariant oracles |
| Expensive or unavailable exact outputs | Metamorphic relations grounded in domain semantics |
| Stateful workflows or protocols | Model-based command sequences with preconditions, transitions, and postconditions |
| Independent implementations or modes | Differential comparison with explicit normalization rules |
| Weak assertions or missing observations | Mutation testing classified by reachability, infection, propagation, and revealability |
| Races or timing windows | Deterministic barriers, controlled schedulers, bounded schedule exploration, and race detection |
| Recovery and resource behavior | Fault injection at acquisition, use, release, timeout, cancellation, and partial-completion seams |

Read `references/adversarial-techniques.md` when choosing or combining these methods; use it to define generators, oracles, replay artifacts, bounds, and technique-specific limitations. Do not add a tool or framework merely because the technique exists; match local capabilities and risk.

**Complete when:** each selected method closes a named ledger gap, has an oracle and budget, and records what its passing result cannot establish.

### 5. Run the falsification loop

For each prioritized ledger row:

1. State the concrete hypothesis: which input, state, schedule, dependency outcome, or resource condition may violate which contract.
2. Add the smallest test or generated harness capable of falsifying it.
3. Confirm the oracle observes the real contract, including relevant state changes, outputs, emitted effects, cleanup, and forbidden side effects.
4. Run the focused case under controlled conditions. Treat crashes, hangs, leaks, nondeterminism, unexpected success, wrong failure classes, and corrupted state as findings.
5. Minimize a failing input, trace, state sequence, schedule, or fault set while preserving the failure.
6. Record concrete replay data: minimized case, environment, versions, configuration, seed when relevant, schedule or event trace, and injected fault.
7. Deduplicate by violated contract and cause, not merely by stack trace or surface symptom.

For generated work, exercise valid structured inputs, malformed inputs, and stateful sequences as applicable. Measure the produced distribution across named partitions. Preserve the concrete counterexample; a seed alone may not replay after generator or tool changes.

**Complete when:** each executed row has reproducible evidence, a bounded clean result, or a classified finding with a minimized reproducer.

### 6. Triage and repair without laundering failures

Classify each finding before changing code:

- **Product defect:** the implementation violates the supported contract or invariant.
- **Test defect:** the setup, oracle, subject, isolation, or expected result is wrong.
- **Environment or harness defect:** the runner, fixture, platform, or dependency makes the result invalid.
- **Specification gap:** behavior is material but no authority defines the expected outcome.
- **Flake:** identical code and declared configuration produce both pass and fail outcomes.

For an authorized product defect, first retain a test that fails for the faulty behavior, then make the smallest responsible correction and prove the test passes. For an audit-only request, report the reproducer and proposed repair without editing product code.

Investigate flakes as possible product defects. Replace sleeps with observable completion, control time and randomness, remove order dependence and leaked state, and capture failing seeds or schedules. Reruns and quarantine are temporary containment only; they require a visible owner, reason, and exit condition.

When the expected behavior is genuinely undefined, stop guessing. Surface the decision with the smallest counterexample and the competing interpretations.

**Complete when:** no finding has been converted into unexplained skip, weakened evidence, retry noise, or a broader catch; every disposition is supported and authorized.

### 7. Audit suite strength and prune carefully

Read `references/suite-evidence.md` when assessing coverage, mutation results, oracle strength, test smells, flakes, or removal candidates; use it to build converging evidence instead of optimizing one score.

Challenge retained tests:

- Would the test fail if the relevant decision, state update, cleanup, or effect were broken?
- Does the assertion inspect the correct subject, type, path, state, and non-effect?
- Does a mock assert an essential boundary contract or merely mirror implementation calls?
- Does a snapshot expose the semantic difference that matters?
- Does the test add a unique partition, transition, oracle, mutant kill, historical defect, platform condition, or diagnostic signal?
- Can it run alone, reordered, in the normal suite, and concurrently where the runner supports those modes?

Treat smell detectors as prompts for investigation. Multiple assertions may jointly prove one behavior; duplicate execution may protect a different oracle or regression. Before consolidating or deleting, compare the original and proposed suite against the same behavior ledger, mutant-kill vector or equivalent fault probes, historical reproducers, environments, and diagnostics. Prefer test selection or prioritization when runtime is the problem and removal evidence is incomplete.

**Complete when:** every retained test has a distinct behavioral purpose, every removal preserves the evidence that matters, and metric or smell changes are interpreted rather than merely reported.

### 8. Make regressions durable and verify broadly

Every confirmed defect gets a minimal deterministic regression at the lowest layer that exposes the violated contract. Name the behavior and scenario, preserve the essential boundary or sequence, and record historical rationale when it will not remain obvious. Add a higher-level regression only when cross-boundary risk warrants it.

Prove durability where practical:

- the regression fails against the defective behavior or a controlled equivalent fault
- it passes after the repair
- it replays without relying only on a seed, wall-clock race, external network, or incidental order
- setup and cleanup survive assertion or execution failure

Run focused tests after each change, then the affected suite and configured broader suite. Repeat under the campaign's declared count and applicable variants such as reordered tests, independent seeds, parallel execution, supported versions, or race/sanitizer instrumentation. Do not hide a broader regression behind focused success.

**Complete when:** every fixed defect has proven regression value, all declared verification commands pass under the agreed repetitions and variants, and no unexplained failure, hang, leak, retry, or flake remains in scope.

### 9. Close the ledger and report limits

Copy `templates/sweep-report.md` when a durable report helps. Report:

- scope, authority, baseline revision, dirty state, environment, and budgets
- ledger coverage by status: covered, confirmed defect, excluded, escalated, or unresolved
- tests added, strengthened, consolidated, removed, or retained, with the distinct behavior each protects
- product, test, and harness defects plus their minimized reproducers and regressions
- exact commands, repetitions, durations, and outcomes
- coverage, mutation, race, sanitizer, fuzz, or model evidence with tool/version and interpretation
- remaining assumptions, unsupported environments, unexecuted techniques, specification gaps, and residual high-risk rows

Do not say “fully tested,” “race-free,” “leak-free,” “exhaustive,” or “strong coverage” without a defined claim and supporting measurement.

**Complete when:** every ledger row is covered, explicitly excluded with evidence, or escalated; every confirmed defect has durable regression protection; every retained test earns its place; all agreed runs are clean; and residual uncertainty is visible.

## Gotchas

1. More cases can repeat the same weak oracle. Improve discriminating power before multiplying volume.
2. Random generation without distribution checks can miss the exact partitions it was meant to explore.
3. A concrete minimized failure is more durable than a seed, count, screenshot, or stack trace alone.
4. Stress repetition can expose a race but rarely explains or reliably replays it; controlled scheduling and explicit barriers are stronger when available.
5. Equivalent mutants, invalid metamorphic relations, shared differential bugs, and mistaken models can create false evidence. Classify limitations instead of forcing a score.
6. Removing a slow test may improve feedback while destroying unique regression value. Try selection, prioritization, or fixture repair before irreversible minimization.
7. Resource exhaustion means testing the contract at bounded failure seams, not crashing the developer's machine or a shared service.

## Reading guide

| Need | Read |
|---|---|
| Choose boundary, combinatorial, property, fuzz, metamorphic, model-based, differential, concurrency, fault-injection, or minimization methods | `references/adversarial-techniques.md` |
| Judge reachability, oracle strength, mutation survivors, flaky behavior, smells, redundancy, or pruning evidence | `references/suite-evidence.md` |
| Record scope, budgets, hypotheses, oracles, and dispositions | `templates/risk-ledger.md` |
| Hand off results, verification, changes, and residual risk | `templates/sweep-report.md` |
