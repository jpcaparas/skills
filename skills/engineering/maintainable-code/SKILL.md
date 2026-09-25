---
name: maintainable-code
description: "Guide maintainable, resilient, test-double-friendly code: clear names, decomposition, safe defaults, idempotency, bounded retries, observability, and quality gates. Use for production code, jobs, queues, webhooks, APIs, refactors, reviews, plans, CI, config, or dependency-heavy code and tests. Skip disposable work."
compatibility: "No external dependencies. Optional helper scripts require python3."
metadata:
  version: "2.0.0"
  short-description: "Keep generated code maintainable, resilient, and testable"
  openclaw:
    category: "development"
    requires:
      bins: [python3]
references:
  - principles
  - decomposition
  - commenting
  - review-rubric
  - implementation-plans
  - guardrails-and-quality-gates
  - resilience
  - jobs-and-queues
  - distributed-systems
  - observability
  - dependency-boundaries
  - test-doubles
  - gotchas
  - source-notes
---

# maintainable-code

Write, edit, and review code so a human maintainer can understand it, test it, and change it later without decoding cleverness, debug production failures without attaching a debugger, and replace dependencies in tests without distorting the production design.

This skill unifies three concerns that used to be separate skills: general maintainability, production-app resilience (jobs, queues, retries, observability), and mockability (dependency boundaries and test doubles).

## Passive Trigger

Load this skill in the background whenever the task involves source code, even if the user does not mention maintainability. This includes production-facing runtime behavior such as background workers, scheduled tasks, webhooks, payment flows, imports/exports, notifications, API integrations, database state transitions, caches, file uploads, queues, cron, auth/session flows, logging, tracing, alerting, or reliability behavior. It also includes any behavior that depends on collaborators, I/O, time, randomness, persistence, configuration, network calls, SDKs, process state, or framework context.

Keep it lightweight for small edits: apply the core rules silently, then mention only the decisions that affect the final implementation. Also load {{ skill:maintainable-tests }} when adding or changing tests, if available.

## Decision Tree

Use the routes below when a non-obvious design decision needs more detail than the core rules or local evidence provide. A matching topic alone does not require reading a reference stack.

- Implementing a new feature or fixing a bug:
  Match the local architecture first. Keep the change small, typed, named plainly, and covered by the narrowest meaningful verification. Write for a future maintainer with solid fundamentals but incomplete context about this system.

- Refactoring existing code:
  Preserve behavior in small steps using adequate existing coverage. Consult `references/decomposition.md` for unclear boundaries and `references/dependency-boundaries.md` when tangled side effects prevent safe verification. Add characterization or a replacement point only where needed.

- Reviewing code:
  Findings must cite concrete code and explain maintainer impact. Consult `references/review-rubric.md` for difficult severity or scope decisions and `references/commenting.md` when non-obvious operational context needs explanation.

- Writing a plan for another agent or teammate:
  Make the outcome, scope, and verification clear without session context. Consult `references/implementation-plans.md` when handoff complexity warrants it, or `references/commenting.md` when non-obvious rationale needs preserving. Include failure and dependency decisions that affect the work, not a fixed section quota.

- Writing operational code, CI workflows, migrations, generated glue, or dense command pipelines:
  Comment on non-obvious intent, invariants, and external constraints. Consult `references/commenting.md` when placement or explanation is unclear; do not narrate obvious code.

- Adding background jobs, queues, cron, webhooks, imports/exports, email, payment capture, or notifications:
  Establish safe duplicate handling, bounded work, and recovery for applicable failure modes. Reuse verified framework or existing guarantees. Consult `references/resilience.md` or `references/jobs-and-queues.md` for unresolved risks, not to add machinery by default.

- Multiple services, external APIs, event publishing, distributed data changes, or async workflows:
  Bound waits and retries, prevent harmful duplicates, and account for partial completion. Consult `references/distributed-systems.md` where the ownership or guarantee is unclear; outbox/inbox, reconciliation, and compensation are options, not a universal stack.

- Adding logging, metrics, tracing, alerts, dashboards, or incident diagnosis:
  Use existing signals that explain user impact and recovery. Consult `references/observability.md` when a diagnostic gap warrants instrumentation, not to add telemetry for every edit.

- Choosing strict runtime defaults, environment-scoped safety rails, compatibility policy, or repository quality gates:
  Separate configured, applicable, selected, and successfully applied states; make dangerous effects opt-in; stage behavior-changing defaults; and verify the advertised compatibility range. Consult `references/guardrails-and-quality-gates.md` when the policy needs further design.

- Adding code that calls a dependency, or making hard-to-test code replaceable:
  Keep external integrations behind narrow ports/adapters or equivalent local boundaries; separate domain policy from construction, configuration, and transport. Control time, randomness, and environment reads at a boundary. Consult `references/dependency-boundaries.md` when an existing seam is inadequate.

- Choosing how to replace a dependency in tests:
  Prefer the least powerful double that proves the behavior: stub for canned answers, fake for realistic in-memory behavior, mock or spy for interaction contracts. Consult `references/test-doubles.md` for non-obvious substitution or adapter-drift risks.

- Unsure whether a design is maintainable:
  Choose the option that reduces future reader effort without hiding important domain behavior. Consult `references/principles.md` or the reference for the specific unresolved risk.

- The user asks for cleverness, compression, or broad abstraction:
  Honor the requested tradeoff without asking them to restate it. Keep correctness, types, and safety intact; contain cleverness where practical and explain only consequential maintenance costs.

## Quick Reference

| Situation | Default action |
|---|---|
| New code | Use existing local patterns, precise names, strong types, and direct control flow |
| Repeated logic | Extract only after the duplication has the same reason to change |
| Complex branch | Normalize inputs early, guard invalid cases, then keep the happy path visible |
| Operational script or CI YAML | Name each phase and comment non-obvious command groups, external API quirks, artifact contracts, and failure handling |
| Large function | Split by stable responsibilities, not by arbitrary line count |
| New abstraction | Require at least two real call sites or a clear boundary being protected |
| Silent framework behavior | Prefer a fail-loud or immutable default when compatibility evidence supports it; treat the switch as a behavior migration |
| Dangerous or overwriting operation | Default it off; use confirmation in interactive tools, and explicit intent, scope, preconditions, idempotency, and recovery appropriate to programmatic contracts |
| Quality policy | Provide one check-mode command that composes the configured layers: formatting/lint, analysis, behavior tests, and safe refactor dry-runs only when that tooling exists |
| Version compatibility | Use the stack's supported seam—runtime capability check, versioned adapter, build flag, or conditional compilation—and test the lowest supported combination as well as current versions |
| Comments | Explain non-obvious rationale or constraints at the smallest useful scope; use ASCII diagrams only when they clarify the flow |
| Plans | Give enough scope, local context, and verification evidence for the requested outcome |

Resilience:

Apply these only where the risk exists. Existing database, provider, framework, and platform guarantees count when their scope and configuration cover the operation; add mechanisms only for gaps.

| Situation | Default action |
|---|---|
| Duplicate browser submit, webhook replay, retry, or worker restart | Prevent harmful duplicate effects with natural idempotency, uniqueness, or a durable intent key |
| Ten users trigger the same expensive job | Coalesce the same authorized intent atomically and bound concurrent execution; reuse existing job status |
| Job stays `pending` or `running` too long | Ensure stale work is detected and safely recovered or made terminal; use existing queue recovery when sufficient |
| Remote API call | Ensure bounded connection/request waits; if retrying, classify errors and use a bounded, safe backoff policy |
| Queue load spike | Bound resource use and protect shared dependencies using existing capacity controls or backpressure |
| Side effect after database write | Ensure required handoff is not lost; use a transactional facility, outbox, or other proven recovery path |
| Multi-step distributed workflow | Make states and partial-completion outcomes explicit; reconcile or compensate where necessary |
| Partial outage | Degrade lower-value features first and preserve the core user task |
| Logging request/job progress | Include safe context needed to identify the work, outcome, and recovery decision |
| Metrics | Measure relevant user-health and capacity risks; reuse existing metrics before adding counters |
| Tracing | Add spans for unexplained cross-boundary latency or failures, not tiny local helpers |
| Alert | Page only on user impact or exhausted automation; use non-paging signals only when they support diagnosis or action |

Testability:

| Situation | Default action |
|---|---|
| Direct network, database, file, clock, random, env, or queue access | Keep it at an outer boundary or pass it in behind a small contract |
| Business rule mixed with an SDK call | Extract the rule into a deterministic function and inject the SDK-facing adapter |
| Constructor creates clients internally | Accept the client, factory, or configuration from the caller unless local patterns say otherwise |
| Static/global singleton dependency | Prefer an explicit collaborator, context object, or narrow wrapper at the boundary |
| Framework handler | Keep parsing and response formatting in the handler; move policy into callable services/functions |
| Tests need real external services | Use a fake, stub, contract test, or local test container before hitting shared infrastructure |
| Interface seems useful | Add it only when there is real substitution, a boundary to protect, or a language convention requiring it |
| Unmockable code found in review | Cite the hidden dependency and show the smallest repair path, not a blanket rewrite |
| Tests | Reuse adequate coverage; fill behavior or regression gaps before risky changes |
| Review | Prioritize defects, confusing boundaries, missing tests, and future-change hazards |

## Core Rules

Clarity and structure:

1. Optimize for the next competent maintainer, not for demonstrating sophistication. Assume they have good fundamentals, but not the system history in your head.
2. Read the surrounding code before naming, extracting, or introducing patterns.
3. Keep behavior close to the data and policy that explain it.
4. Prefer boring typed data shapes over strings, bags of options, or hidden conventions.
5. Keep functions at one stable level of abstraction: orchestration, policy, transformation, or I/O.
6. Make invalid states hard to represent when the language and codebase support it.
7. Comment only on non-obvious rationale, invariants, or constraints that names and structure cannot express. Put the explanation at the relevant class, method, property, branch, or block; do not add commentary for the user to prune.
8. Verify uncertain, version-sensitive, or consequential language/framework claims against official sources for the project's actual stack. Link sources when they help verify the claim or the user requests them; do not research known basics by default or overstate documented behavior.
9. Add compact ASCII diagrams inside comments or docblocks when they clarify non-obvious data flow, state transitions, queues, retries, ownership, or boundary crossings. Keep the diagram and prose consistent; if code changes make either stale, update both immediately.
10. Refactor non-trivial behavior with adequate verification; reuse existing tests and add characterization only for gaps.
11. State consequential tradeoffs in the final answer when you intentionally leave complexity in place.
12. Layer strictness across types, analysis, framework behavior, and boundary validation where local compatibility permits. Add migration coverage before enabling a behavior-changing strict mode.
13. Classify cancellation, optional capability absence, operational failure, and unexpected defects separately at entry points. Preserve actionable causes instead of collapsing every outcome to `false`, `null`, or one generic error.
14. Keep dangerous capabilities off by default. A force flag may skip interaction, but it must not bypass authorization, validation, invariants, or recovery checks.

Production behavior and recovery:

15. Treat retries, duplicate delivery, concurrency, latency, partial failure, deploy restarts, and stale state as normal inputs, not unusual accidents.
16. Distinguish new intent from replay when duplicates could harm correctness or resource use. Natural idempotency or existing identity may suffice; do not persist new work records without a need.
17. Give non-trivial persistent work explicit allowed transitions, ownership, terminal outcomes, and a bounded path out of stuck states. Use only the states and fields the workflow needs.
18. Ensure applicable failures have safe recovery or a clear terminal outcome. Prefer existing automatic recovery; add retries, sweepers, reconciliation, or dead-letter handling only for uncovered risks.
19. Bound resource use so one workflow cannot exhaust shared capacity. Existing concurrency limits, leases, rate limits, or backpressure may suffice; queues and bulkheads are not mandatory additions.
20. Prevent harmful duplicate side effects at the boundary that can enforce it. Verify the scope of natural idempotency, database constraints, provider keys, or other existing guarantees before adding deduplication machinery.
21. Ensure waits across process, network, queue, database, or provider boundaries are bounded. Respect effective existing deadlines rather than adding competing timeout layers; make uncertain outcomes safe to recover.
22. Use enough observability to diagnose relevant user-health and capacity failures; latency, traffic, errors, and saturation are useful starting questions, not a telemetry quota. Never log secrets, tokens, raw payment details, full PII, session cookies, or provider credentials.

Testability:

23. Separate decisions from effects. Domain policy should be testable without real networks, clocks, files, databases, queues, or randomness.
24. Make collaborators explicit at module, constructor, function, handler, or context boundaries, and prefer narrow contracts that describe what the caller needs, not everything the dependency can do.
25. Use fakes for stateful behavior, stubs for fixed responses, mocks/spies for important interactions, and contract tests for adapters. Mockable code is not the same as mock-heavy tests.
26. Do not add abstractions with only imaginary substitutes, or expose private internals just so tests can reach them. Simple code with one clear replacement point beats layers of unused interfaces.

## Maintainability Gate

Before finishing code changes, run this gate mentally and with local tooling where available:

| Gate | Pass condition |
|---|---|
| Intent | A reader can tell what the code does from names and structure before reading every line |
| Scope | The change touches the smallest responsible surface and avoids unrelated cleanup |
| Boundaries | I/O, orchestration, domain policy, and presentation are not tangled without reason |
| Types | Data contracts are explicit enough for editor, compiler, or tests to catch misuse |
| Comments | Dense or surprising code has digestible comments/docblocks at the right level: class/module, method/function, property/field, and local block where useful; any ASCII diagram agrees with the prose and code |
| Tests | The most likely regression has a focused test or a clearly stated verification gap |
| Errors | Failure modes are handled at the boundary that can add useful context |
| Defaults | Strictness, immutability, and environment gates are explicit, configurable where appropriate, and adopted with compatibility evidence |
| Automation | Local and CI check modes enforce the same versioned quality policy and cover the supported dependency range |
| Handoff | The final response names key files, verification run, and any remaining risk |

## Self-Healing Gate

For production runtime changes, check the applicable guarantees below. Accept adequate existing mechanisms; the table is not a requirement to add every state, signal, or recovery component.

| Gate | Pass condition |
|---|---|
| Identity | Harmful duplicate effects are prevented through natural idempotency, durable intent identity, uniqueness, or another proven boundary guarantee |
| State | Non-trivial work has explicit transitions and terminal/recovery behavior for the states it actually uses |
| Concurrency | Shared resources have uniqueness, locking, leases, rate limits, or worker caps |
| Time | Remote calls, jobs, locks, and pending states have timeouts or expiration |
| Retries | Retryable errors are classified, bounded, jittered, and safe against duplicate side effects |
| Recovery | Stuck, partial, and failed states can be retried, reconciled, redriven, or made terminal without a developer editing data by hand |
| Degradation | The app preserves the most important user task when optional dependencies fail |
| Observability | Available signals explain relevant user impact, work identity, failure, and recovery outcomes |
| Alerts | Alerts fire on exhausted automation or user impact, not on every expected transient failure |
| Tests | The most likely production failure has a focused test, simulation, or stated verification gap |

## Mockability Gate

Before finishing a change that touches dependencies or side effects, also check:

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

Scale this process to the change. Small edits need focused context and verification, not a written story, failure map, or multi-section report.

1. Recon first.
   Read the local guidance, affected code, relevant contracts, and tests needed to act correctly. Inspect wider wiring or configuration only when the change depends on it.

2. Identify the maintainer story.
   Understand the responsibility being added or changed. Write it down only when it helps resolve scope or handoff ambiguity.

3. Draw the failure map.
   For material runtime risks, consider relevant duplicate input, concurrency, timeouts, crashes, stale state, and partial completion. Identify the existing owner or missing guarantee; record only decisions needed for implementation or review.

4. Identify hard dependencies.
   Inspect affected I/O, time, randomness, config, SDK, and global-state boundaries. Reuse safe replacement points; do not inventory unrelated dependencies.

5. Choose the simplest boundary that fits the codebase.
   Prefer existing modules and helpers. Add a new abstraction only when it protects a real axis of change. Prefer local constraints and existing framework primitives; add queues, locks, outbox tables, circuit breakers, or watchdogs only when the failure mode is real enough to justify them.

6. Implement in narrow steps.
   Keep the diff reviewable. Avoid drive-by formatting, unrelated migrations, style churn, and test-only contortions such as public setters or broad service locators added solely for tests.

7. Verify behavior, failure behavior, and readability.
   Run relevant tests and required repository checks. Reuse adequate coverage and fill consequential gaps. Re-read the diff as if reviewing a stranger's code, commenting only where non-obvious rationale would otherwise be lost.

8. Report plainly.
   Report the outcome, verification, and remaining risk. Include design decisions only when consequential; omit empty sections and routine process narration.

## Optional Helpers

Use the helpers as fast smell scanners, not as verdicts:

```bash
python3 scripts/analyze_maintainability.py /path/to/project
python3 scripts/analyze_maintainability.py /path/to/project --json
python3 scripts/analyze_app_resilience.py /path/to/project
python3 scripts/analyze_app_resilience.py /path/to/project --json
python3 scripts/analyze_mockability.py /path/to/project
python3 scripts/analyze_mockability.py /path/to/project --json
```

- `analyze_maintainability.py` flags large functions, vague names, weak types, comment debt, and TODO drift. Function-span and function-name checks use Python's AST only; calls and function forms in every other advertised language are deliberately omitted rather than guessed, while weak-type signals remain limited to Python annotations and conservative TypeScript type positions.
- `analyze_app_resilience.py` flags likely missing idempotency, retry/backoff gaps, external calls without obvious timeouts, low-context logs, swallowed errors, and pending states without recovery.
- `analyze_mockability.py` flags likely hardcoded effects and globals so a human or agent can inspect them.

Treat their output as prompts for human review. A quiet scan does not prove code is good, resilient, or mockable, and a noisy scan does not prove code is bad. For deeper reviews, optionally adapt `templates/maintainability-review.md`, `templates/resilience-review.md`, or `templates/mockability-review.md`; their format and sections are not required.

## When Guidance Stops Helping

Prefer demonstrated local invariants and idiomatic framework behavior over a bundled pattern. When these conflict or advice fails, inspect the installed version and relevant official documentation or trusted primary sources. State unresolved limits. Propose a canonical skill correction or deletion with the conflicting rule, source/version, and a concrete regression or counterexample; do not silently edit an installed copy or turn the finding into an unrelated refactor.

## Reading Guide

| Need | Read |
|---|---|
| Principles behind the defaults | `references/principles.md` |
| Splitting functions, modules, and responsibilities | `references/decomposition.md` |
| Useful developer comments and language-specific examples | `references/commenting.md` |
| Review findings and severity ordering for maintainability, resilience, and testability | `references/review-rubric.md` |
| Plans for other agents or teammates | `references/implementation-plans.md` |
| Strict defaults, dangerous effects, compatibility, and executable quality gates | `references/guardrails-and-quality-gates.md` |
| Self-healing app principles, failure maps, work identity, and state machines | `references/resilience.md` |
| Jobs, queues, webhooks, cron, stuck work, and duplicate work | `references/jobs-and-queues.md` |
| Retries, timeouts, idempotent APIs, outbox/inbox, sagas, and reconciliation | `references/distributed-systems.md` |
| Logging, metrics, tracing, alerts, and dashboards | `references/observability.md` |
| Isolating dependencies, side effects, time, randomness, and configuration | `references/dependency-boundaries.md` |
| Choosing mocks, stubs, fakes, spies, and contract tests | `references/test-doubles.md` |
| Common traps and anti-patterns across all three concerns | `references/gotchas.md` |
| Source influence and adaptation notes | `references/source-notes.md` |

## Gotchas

1. Small functions are not automatically maintainable. Fragmentation can hide the story as badly as a long function.
2. DRY is not a command to merge coincidentally similar code. Shared code should share a reason to change.
3. "Clean" code can still be wrong. Preserve behavior and verify before polishing structure.
4. Generic abstractions often age worse than explicit duplication. Wait for real variation.
5. Comments cannot rescue misleading names or tangled boundaries. Rename or restructure first.
6. Agent-generated code often passes tests while violating local idioms. Match the repo before applying global advice.
7. A stricter default can be a breaking behavioral change even when it looks like configuration. Inventory affected paths and stage the rollout.
8. A green unit suite does not replace the repository's configured formatter/linter checks, analysis, compatibility testing, or safe codemod dry-runs when available; each catches a different maintenance failure.
9. Retrying unsafe work can create the outage you were trying to heal. Make the operation idempotent before adding retries.
10. A unique job is not enough if the lock expires before the worker finishes. Align lock TTL, job timeout, visibility timeout, and retry window.
11. `pending` is not a recovery strategy. Every non-terminal state needs an owner and a stale-state path.
12. Dead-letter queues are not trash cans. They need alarms, inspection fields, redrive rules, and a policy for poison messages.
13. More observability is not automatically better. High-cardinality, secret-bearing, or unqueried telemetry creates cost and risk without improving recovery.
14. Interfaces for every class make code harder to navigate. Add contracts where substitution or ownership boundaries are real.
15. Hidden reads from clocks, random generators, environment variables, and global context often break tests as much as network calls do.
16. Monkeypatching can be useful, but it should not be the only way to replace a collaborator in core production code.
