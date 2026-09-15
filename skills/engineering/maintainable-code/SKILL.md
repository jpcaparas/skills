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

What are you doing?

- Implementing a new feature or fixing a bug:
  Match the local architecture first. Keep the change small, typed, named plainly, and covered by the narrowest meaningful verification. Write for a future maintainer with solid fundamentals but incomplete context about this system.

- Refactoring existing code:
  Preserve behavior in small steps. Read `references/decomposition.md` before splitting modules, extracting helpers, or changing boundaries. If the code is hard to test because of tangled side effects, also read `references/dependency-boundaries.md` and move side effects behind the smallest useful boundary before changing behavior.

- Reviewing code:
  Use the severity-first rubric in `references/review-rubric.md`, including its resilience and testability scopes when the diff touches runtime behavior or dependencies. Findings must cite concrete code and explain maintainer impact. If the diff includes CI, shell, config, migrations, generated glue, or dense cross-boundary code, also read `references/commenting.md`.

- Writing a plan for another agent or teammate:
  Read `references/implementation-plans.md`. Make the plan self-contained enough for a weaker executor with no session context. Include the failure map and dependency boundaries where they apply. If the plan touches operational or dense code, call out where developer comments are required and read `references/commenting.md`.

- Writing operational code, CI workflows, migrations, generated glue, or dense command pipelines:
  Read `references/commenting.md`. Add comments that teach intent, invariants, external constraints, and the shape of multi-step logic.

- Adding background jobs, queues, cron, webhooks, imports/exports, email, payment capture, or notifications:
  Read `references/resilience.md` and `references/jobs-and-queues.md`. Require stable work identity, idempotency, bounded concurrency, retry limits, stale-work recovery, dead-letter handling, and worker timeouts.

- Multiple services, external APIs, event publishing, distributed data changes, or async workflows:
  Read `references/distributed-systems.md`. Design timeouts, retry budgets, outbox/inbox handling, deduplication, reconciliation, and compensating actions.

- Adding logging, metrics, tracing, alerts, dashboards, or incident diagnosis:
  Read `references/observability.md`. Instrument the decision points that explain user impact and recovery, not every line of code.

- Choosing strict runtime defaults, environment-scoped safety rails, compatibility policy, or repository quality gates:
  Read `references/guardrails-and-quality-gates.md`. Separate configured, applicable, selected, and successfully applied states; make dangerous effects opt-in; stage behavior-changing defaults; and verify the advertised compatibility range.

- Adding code that calls a dependency, or making hard-to-test code replaceable:
  Read `references/dependency-boundaries.md`. Accept dependencies from the caller where practical, keep domain policy separate from construction, configuration, and transport, and control time, randomness, and environment reads at a boundary.

- Choosing how to replace a dependency in tests:
  Read `references/test-doubles.md`. Prefer the least powerful double that proves the behavior: stub for canned answers, fake for realistic in-memory behavior, mock or spy for interaction contracts.

- Unsure whether a design is maintainable:
  Read `references/principles.md`, then choose the option that reduces future reader effort without hiding important domain behavior. For production runtime behavior, also read `references/resilience.md` and run the Self-Healing Gate below.

- The user asks for cleverness, compression, or broad abstraction:
  Ask whether maintainability still matters. If yes, prefer explicit code. If no, keep the clever part boxed, named, tested, and documented as a local exception.

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
| Comments | Explain why, tradeoffs, invariants, surprising constraints, and learning context at class, method, property, and dense block level; use small ASCII diagrams for non-obvious flows when helpful |
| Plans | Include exact files, local conventions, verification commands, and stop conditions |

Resilience:

| Situation | Default action |
|---|---|
| Duplicate browser submit, webhook replay, retry, or worker restart | Add an idempotency key or deterministic work key and persist the result or state transition |
| Ten users trigger the same expensive job | Coalesce by unique job key, lease one active worker, return the existing job status, and expose progress |
| Job stays `pending` or `running` too long | Add `expires_at` or heartbeat-based stale detection, safe retry or failover, and an audit log entry |
| Remote API call | Set connection and request timeouts, classify retryable errors, use capped backoff with jitter, and stop at a retry budget |
| Queue load spike | Buffer work, cap worker concurrency, use backpressure/rate limits, and protect shared dependencies |
| Side effect after database write | Use an outbox or transactional handoff; make consumers idempotent |
| Multi-step distributed workflow | Model states explicitly and add reconciliation or compensating actions |
| Partial outage | Degrade lower-value features first and preserve the core user task |
| Logging request/job progress | Include correlation ID, actor, work key, state transition, attempt, dependency, duration, and outcome |
| Metrics | Track latency, traffic, errors, saturation, queue age, retry count, dead-letter count, and stale work |
| Tracing | Add spans around cross-boundary calls and durable async handoffs, not tiny local helpers |
| Alert | Page only on user impact or exhausted automation; otherwise create inspectable dashboards or tickets |

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
| Tests | Add characterization before risky refactors and focused regression tests after fixes |
| Review | Prioritize defects, confusing boundaries, missing tests, and future-change hazards |

## Core Rules

Clarity and structure:

1. Optimize for the next competent maintainer, not for demonstrating sophistication. Assume they have good fundamentals, but not the system history in your head.
2. Read the surrounding code before naming, extracting, or introducing patterns.
3. Keep behavior close to the data and policy that explain it.
4. Prefer boring typed data shapes over strings, bags of options, or hidden conventions.
5. Keep functions at one stable level of abstraction: orchestration, policy, transformation, or I/O.
6. Make invalid states hard to represent when the language and codebase support it.
7. Leave useful developer comments where names and structure cannot carry the whole story, especially in CI, shell, config, migrations, concurrency, retries, security, generated glue, and external-service boundaries. Consider class, method, property, branch, and block-level comments or docblocks; the user can prune them later, but missing context is harder to recover.
8. When a comment, docblock, review note, or final answer makes a language or framework claim and official documentation exists, verify and link the current official source for the project's actual stack; paraphrase the documented behavior instead of inventing or overstating it.
9. Add compact ASCII diagrams inside comments or docblocks when they clarify non-obvious data flow, state transitions, queues, retries, ownership, or boundary crossings. Keep the diagram and prose consistent; if code changes make either stale, update both immediately.
10. Refactor with tests or characterization when behavior is non-trivial.
11. State tradeoffs in the final answer when you intentionally leave complexity in place.
12. Layer strictness across types, analysis, framework behavior, and boundary validation where local compatibility permits. Add migration coverage before enabling a behavior-changing strict mode.
13. Classify cancellation, optional capability absence, operational failure, and unexpected defects separately at entry points. Preserve actionable causes instead of collapsing every outcome to `false`, `null`, or one generic error.
14. Keep dangerous capabilities off by default. A force flag may skip interaction, but it must not bypass authorization, validation, invariants, or recovery checks.

Production behavior and recovery:

15. Treat retries, duplicate delivery, concurrency, latency, partial failure, deploy restarts, and stale state as normal inputs, not unusual accidents.
16. Give every expensive or side-effecting operation a stable identity. The system should know whether a request is new work, a replay, or a different intent.
17. Prefer explicit state machines over loose status strings. Each state needs allowed transitions, owner, timeout, retry policy, terminal outcomes, and recovery behavior.
18. Put recovery in the application before putting it in a human runbook. Use bounded retries, stale-work sweepers, reconciliation jobs, dead-letter queues, and safe redrive paths.
19. Limit blast radius with queues, leases, rate limits, bulkheads, and backpressure. Do not let one noisy workflow exhaust the whole app.
20. Make side effects idempotent at the boundary that can enforce it: database constraints, unique keys, idempotency tables, outbox/inbox tables, provider idempotency keys, or queue deduplication.
21. Use timeouts everywhere work crosses process, network, queue, database, or provider boundaries. A stuck dependency should become a known state with a bounded recovery path.
22. Start observability from the four golden signals: latency, traffic, errors, and saturation. Add bespoke metrics only after user-health and capacity questions are covered, and never log secrets, tokens, raw payment details, full PII, session cookies, or provider credentials.

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

Before finishing a change that affects production runtime behavior, also check:

| Gate | Pass condition |
|---|---|
| Identity | Duplicate requests, jobs, webhooks, and events map to a stable idempotency or work key |
| State | Non-trivial work has explicit pending/running/succeeded/failed/canceled/stale behavior |
| Concurrency | Shared resources have uniqueness, locking, leases, rate limits, or worker caps |
| Time | Remote calls, jobs, locks, and pending states have timeouts or expiration |
| Retries | Retryable errors are classified, bounded, jittered, and safe against duplicate side effects |
| Recovery | Stuck, partial, and failed states can be retried, reconciled, redriven, or made terminal without a developer editing data by hand |
| Degradation | The app preserves the most important user task when optional dependencies fail |
| Observability | Logs, metrics, and traces explain user impact, work identity, state transitions, attempts, dependency health, and recovery outcomes |
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

1. Recon first.
   Read local docs, nearby code, package scripts, handlers, jobs, schemas, provider adapters, queue config, logging conventions, dependency-injection and test fixture patterns, and tests before designing the change.

2. Identify the maintainer story.
   Write down the responsibility being added or changed. If it needs more than one sentence, split the work or name the sub-responsibilities.

3. Draw the failure map.
   For production-facing changes, list duplicate input, concurrent input, dependency timeout, provider 429/5xx, worker crash, deploy restart, database conflict, stale state, and partial completion. Keep the list proportional to feature risk, and decide which mechanism owns each recovery path: request handler, queue worker, scheduler, reconciliation job, database constraint, provider idempotency feature, or operator-facing tool.

4. Identify hard dependencies.
   List real I/O, time, randomness, config, SDK, database, framework, and global-state touches. Decide which ones stay at the boundary and which need an explicit replacement point.

5. Choose the simplest boundary that fits the codebase.
   Prefer existing modules and helpers. Add a new abstraction only when it protects a real axis of change. Prefer local constraints and existing framework primitives; add queues, locks, outbox tables, circuit breakers, or watchdogs only when the failure mode is real enough to justify them.

6. Implement in narrow steps.
   Keep the diff reviewable. Avoid drive-by formatting, unrelated migrations, style churn, and test-only contortions such as public setters or broad service locators added solely for tests.

7. Verify behavior, failure behavior, and readability.
   Run available tests, typechecks, linters, or focused helper scripts. Cover duplicate input, retry, timeout, stale work, and dependency failure where practical. Re-read the diff as if you were reviewing a stranger's code, and add comments where the next reader would otherwise need session context.

8. Report plainly.
   Explain what changed, why this shape is maintainable, the edge cases and failsafes handled, the dependency boundaries and test doubles used, what was verified, and what risk remains.

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

Treat their output as prompts for human review. A quiet scan does not prove code is good, resilient, or mockable, and a noisy scan does not prove code is bad. For deeper reviews, use `templates/maintainability-review.md`, `templates/resilience-review.md`, and `templates/mockability-review.md`.

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
