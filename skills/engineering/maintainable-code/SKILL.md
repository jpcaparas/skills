---
name: maintainable-code
description: "Passive: use when writing, refactoring or reviewing production source, jobs, webhooks, APIs, CI or config. Covers naming, decomposition, comments, safe defaults, idempotency, bounded retries, queue recovery, observability, dependency boundaries and quality gates, and turning a recurring mistake or session learning into a validator, normalizer, fixture or CI check. Not for disposable scripts."
compatibility: "Optional smell-scanner scripts need python3."
---

# maintainable-code

Write and review code so the next competent maintainer, with solid fundamentals but none of this session's context, can understand it, test it, and debug its failures in production without a debugger. Match the surrounding code's patterns before applying anything here. For small edits apply these rules silently and mention only decisions that change the result; a rename needs no new tests, comments, failure map or doc research. Load `maintainable-tests` when adding or changing tests, if available.

## Code

- Keep one level of abstraction per function (orchestration, policy, transformation, I/O). Split by stable responsibility, not line count. Extract duplication only when the copies share a reason to change; add an abstraction only with two real call sites or a real boundary to protect. Interfaces with imaginary substitutes and public setters added for tests are worse than a single clear replacement point.
- Prefer typed data shapes over strings and option bags; make invalid states unrepresentable where the language allows.
- Normalize inputs early, guard invalid cases, keep the happy path visible. At entry points keep cancellation, absent optional capability, operational failure and unexpected defects distinct with actionable causes; do not collapse them into `false`, `null` or one generic error.
- Refactor non-trivial behaviour only with adequate coverage; reuse existing tests and add characterization only for gaps. Preserve behaviour before polishing structure.
- State consequential tradeoffs in the final answer when you deliberately leave complexity in place. Report key files, verification run and remaining risk; omit empty sections.
- When the user asks for cleverness or compression, do it, keep correctness and types intact, and mention only consequential maintenance costs.

## Comments

Comment only non-obvious rationale, invariants, external contracts (API quirks, file formats, rate limits, runtime quirks), the phase of a dense block, and what breaks if a future maintainer "simplifies" it. Rename or restructure before commenting; never narrate syntax and never add comments for the user to prune later. Put each comment at the smallest useful scope: module or class (responsibility, lifecycle), method (side effects, errors, idempotency), field (units, nullability, persisted format, why a weak type is safe), branch or block (invariant, workaround), trailing only for short source notes. Dense operational code (CI YAML, shell pipelines, migrations, generated glue) needs phase names and artifact contracts commented; generated files say how to regenerate.

When a data flow, state machine, retry loop or ownership relationship is hard to follow in prose, put a compact ASCII diagram (`+ - | > <`, no box drawing) in the docblock, with labels that match real names, and update diagram and prose together; delete it if it cannot be repaired. Back uncertain, version-sensitive or consequential claims about a framework or language with the project's version-matched official docs, paraphrased and linked when that helps a maintainer verify it; do not research known basics.

## Production behaviour

Retries, duplicate delivery, concurrency, latency, partial failure, restarts and stale state are normal inputs. Apply what follows only where the risk exists, and credit existing database, queue, provider and framework guarantees whose scope and configuration actually cover the operation; add queues, locks, outbox tables, breakers or watchdogs only for real gaps.

- Duplicates: prevent harmful duplicate effects at the boundary that can enforce it: natural idempotency, a uniqueness constraint, a durable intent key, a provider idempotency key. Make an operation idempotent before retrying it. Coalesce identical concurrent intent atomically (one report job per account per month; return the existing authorised job) and bound concurrent execution.
- State: non-trivial persistent work has allowed transitions, an owner, terminal outcomes and a bounded path out of stuck states. `pending` is not a recovery strategy; every non-terminal state needs a stale-work path that needs no manual data edit.
- Time: bound every wait across process, network, queue, database or provider. An outcome that is unknown after a timeout (the provider may have acted) is reconciled before it is retried. Retry only classified transient errors, with bounded backoff and jitter, inside the remaining budget; never retry auth or schema failures. A lock or uniqueness window shorter than the job's runtime is not protection; align lock TTL, job timeout, visibility timeout and retry window.
- Side effects after a database write must not be lost: transactional enqueue, outbox, or another proven handoff. Multi-step workflows name their partial-completion states and reconcile or compensate.
- Dead-letter queues need alarms, inspection fields and a redrive policy. Degrade lower-value features first and keep the core task working.
- Observability: log enough safe context to identify the work, the outcome and the recovery decision; never secrets, tokens, card data, full PII or session cookies. Reuse existing metrics and spans; add instrumentation only for a diagnostic gap (latency, traffic, errors, saturation are starting questions). Page only on user impact or exhausted automation. High-cardinality or unqueried telemetry is cost without recovery value.

## Testability

Separate decisions from effects. Keep network, database, files, clock, randomness, environment reads and global state at an outer boundary or behind a narrow contract that exposes only what the caller needs; business rules sit in deterministic functions with the SDK-facing adapter injected. Callers supply clients, factories or configuration rather than constructors building them, unless local patterns say otherwise. Framework handlers parse and format; policy lives in callable services.

Use the least powerful test double that proves the behaviour: a stub for canned answers, a fake for realistic stateful behaviour, a mock or spy only for an interaction that is itself the contract, and contract tests for adapters, so a fake cannot drift from the real dependency. Assert behaviour, not incidental call order. Monkeypatching must not be the only way to replace a collaborator in core code. Cite the hidden dependency and the smallest repair path when you find unmockable code in review; do not prescribe a blanket rewrite.

## Defaults and quality gates

Read `references/guardrails-and-quality-gates.md` when choosing strict runtime defaults, environment-scoped safety rails, dangerous operations, compatibility policy or repository quality gates. The rules that matter: dangerous capabilities are off by default and a `force` flag skips only the prompt, never authorization, validation or recovery; configured, applicable, selected and applied are different states; a stricter default is a behaviour migration to inventory and stage; provide one non-mutating check command composing format, lint, analysis, safe refactor dry-run and tests, and test the lowest supported dependency combination as well as the current one.

## Recurring mistakes

When the same mistake keeps coming back, or the user asks to codify a learning or to make model-generated output (art, prose, a scaffold) more repeatable, read `references/deterministic-checks.md`. Convert it into a check only when it reduces to an invariant code can inspect; enforce it with the smallest mechanism the repository already has (formatter, schema, linter, check mode) before writing a new one, and leave taste as review guidance.

## Reviewing and plans

Lead with findings ordered by maintainer impact: correctness or data risk, test gaps that make change unsafe, confusing ownership, over-generalised or under-named abstractions, error handling and observability gaps, missing context in dense code, then style. Cite file and line, the concrete impact, and a repair direction; no compliments or broad summaries first, and if there are no findings say so and name residual risk. Technical facts beat taste; "nit" is only for non-blocking polish. Recommend an extraction only if you can name the boundary and why it changes independently.

A plan for another agent or teammate is self-contained: outcome, scope, affected boundaries, observable completion criteria, verification and material stop conditions, including failure and dependency decisions that affect the work. Choose the structure that fits; no fixed section quota.

## Gotchas

- Small functions are not automatically maintainable; fragmentation hides the story as badly as a long function.
- Generic abstractions age worse than explicit duplication until real variation appears.
- Agent-written code often passes tests while violating local idioms.
- A green unit suite does not replace the repository's formatter, linter, analysis, compatibility matrix or codemod dry-runs.
- Hidden reads from clocks, random generators, environment variables and global context break tests as much as network calls.

## Smell scanners

`scripts/analyze_maintainability.py`, `scripts/analyze_app_resilience.py` and `scripts/analyze_mockability.py` take a project path (and `--json`) and surface candidate smells: large or vaguely named functions, weak types, comment debt, TODO drift; missing idempotency, retry or timeout handling, swallowed errors, pending states without recovery; hardcoded effects and globals. Function spans and names are Python-only (AST); other languages get conservative signals. Their output is leads to inspect; a quiet scan proves nothing.
