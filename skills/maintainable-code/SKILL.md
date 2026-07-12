---
name: maintainable-code
description: "Passive guidance for maintainable code: decomposition, readable names, safe defaults, side-effect guardrails, compatibility, quality gates, and useful comments. Use when writing, editing, refactoring, reviewing, or planning production code, CI, scripts, configuration, tests, or technical debt. Skip non-code writing and disposable experiments."
compatibility: "No external dependencies. Optional helper scripts require python3."
metadata:
  version: "1.1.0"
  short-description: "Keep generated code simple, decomposed, and reviewable"
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
  - gotchas
  - source-notes
---

# maintainable-code

Write, edit, and review code so a human maintainer can understand it, test it, and change it later without decoding cleverness.

## Passive Trigger

Load this skill in the background whenever the task involves source code, even if the user does not mention maintainability. Keep it lightweight for small edits: apply the core rules silently, then mention only the decisions that affect the final implementation.

## Decision Tree

What are you doing?

- Implementing a new feature or fixing a bug:
  Match the local architecture first. Keep the change small, typed, named plainly, and covered by the narrowest meaningful verification. Write for a future maintainer with solid fundamentals but incomplete context about this system.

- Refactoring existing code:
  Preserve behavior in small steps. Read `references/decomposition.md` before splitting modules, extracting helpers, or changing boundaries.

- Reviewing code:
  Use the severity-first rubric in `references/review-rubric.md`. Findings must cite concrete code and explain maintainer impact. If the diff includes CI, shell, config, migrations, generated glue, or dense cross-boundary code, also read `references/commenting.md`.

- Writing a plan for another agent or teammate:
  Read `references/implementation-plans.md`. Make the plan self-contained enough for a weaker executor with no session context. If the plan touches operational or dense code, call out where developer comments are required and read `references/commenting.md`.

- Writing operational code, CI workflows, migrations, generated glue, or dense command pipelines:
  Read `references/commenting.md`. Add comments that teach intent, invariants, external constraints, and the shape of multi-step logic.

- Choosing strict runtime defaults, environment-scoped safety rails, compatibility policy, or repository quality gates:
  Read `references/guardrails-and-quality-gates.md`. Separate configured, applicable, selected, and successfully applied states; make dangerous effects opt-in; stage behavior-changing defaults; and verify the advertised compatibility range.

- Unsure whether a design is maintainable:
  Read `references/principles.md`, then choose the option that reduces future reader effort without hiding important domain behavior.

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
| Tests | Add characterization before risky refactors and focused regression tests after fixes |
| Plans | Include exact files, local conventions, verification commands, and stop conditions |
| Review | Prioritize defects, confusing boundaries, missing tests, and future-change hazards |

## Core Rules

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

## Operating Workflow

1. Recon first.
   Read local docs, nearby code, package scripts, and tests before designing the change.

2. Identify the maintainer story.
   Write down the responsibility being added or changed. If it needs more than one sentence, split the work or name the sub-responsibilities.

3. Choose the simplest boundary that fits the codebase.
   Prefer existing modules and helpers. Add a new abstraction only when it protects a real axis of change.

4. Implement in narrow steps.
   Keep the diff reviewable. Avoid drive-by formatting, unrelated migrations, and style churn.

5. Verify behavior and readability.
   Run available tests, typechecks, linters, or focused helper scripts. Re-read the diff as if you were reviewing a stranger's code, and add comments where the next reader would otherwise need session context.

6. Report plainly.
   Explain what changed, why this shape is maintainable, what was verified, and what risk remains.

## Optional Helper

Use the helper as a fast smell scanner, not as a verdict:

```bash
python3 scripts/analyze_maintainability.py /path/to/project
python3 scripts/analyze_maintainability.py /path/to/project --json
```

Treat its output as prompts for human review. A quiet script does not prove code is good, and a noisy script does not prove code is bad.
Function-span and function-name checks use Python's AST only; calls and function forms in every other advertised language are deliberately omitted rather than guessed, while weak-type signals remain limited to Python annotations and conservative TypeScript type positions.

## Reading Guide

| Need | Read |
|---|---|
| Principles behind the defaults | `references/principles.md` |
| Splitting functions, modules, and responsibilities | `references/decomposition.md` |
| Useful developer comments and language-specific examples | `references/commenting.md` |
| Review findings and severity ordering | `references/review-rubric.md` |
| Plans for other agents or teammates | `references/implementation-plans.md` |
| Strict defaults, dangerous effects, compatibility, and executable quality gates | `references/guardrails-and-quality-gates.md` |
| Common traps and anti-patterns | `references/gotchas.md` |
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
