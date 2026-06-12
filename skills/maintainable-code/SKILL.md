---
name: maintainable-code
description: "Passive coding-quality skill for maintainable, decomposed, readable code. Use when writing, editing, refactoring, reviewing, or planning code involving complexity, naming, tests, boundaries, or tech debt. Do NOT use for non-code writing, one-off shell commands, or intentionally throwaway code."
compatibility: "No external dependencies. Optional helper scripts require python3."
metadata:
  version: "1.0.0"
  short-description: "Keep generated code simple, decomposed, and reviewable"
  openclaw:
    category: "development"
    requires:
      bins: [python3]
references:
  - principles
  - decomposition
  - review-rubric
  - implementation-plans
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
  Match the local architecture first. Keep the change small, typed, named plainly, and covered by the narrowest meaningful verification.

- Refactoring existing code:
  Preserve behavior in small steps. Read `references/decomposition.md` before splitting modules, extracting helpers, or changing boundaries.

- Reviewing code:
  Use the severity-first rubric in `references/review-rubric.md`. Findings must cite concrete code and explain maintainer impact.

- Writing a plan for another agent or teammate:
  Read `references/implementation-plans.md`. Make the plan self-contained enough for a weaker executor with no session context.

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
| Large function | Split by stable responsibilities, not by arbitrary line count |
| New abstraction | Require at least two real call sites or a clear boundary being protected |
| Comments | Explain why, tradeoffs, invariants, and surprising constraints; do not narrate syntax |
| Tests | Add characterization before risky refactors and focused regression tests after fixes |
| Plans | Include exact files, local conventions, verification commands, and stop conditions |
| Review | Prioritize defects, confusing boundaries, missing tests, and future-change hazards |

## Core Rules

1. Optimize for the next competent maintainer, not for demonstrating sophistication.
2. Read the surrounding code before naming, extracting, or introducing patterns.
3. Keep behavior close to the data and policy that explain it.
4. Prefer boring typed data shapes over strings, bags of options, or hidden conventions.
5. Keep functions at one stable level of abstraction: orchestration, policy, transformation, or I/O.
6. Make invalid states hard to represent when the language and codebase support it.
7. Refactor with tests or characterization when behavior is non-trivial.
8. State tradeoffs in the final answer when you intentionally leave complexity in place.

## Maintainability Gate

Before finishing code changes, run this gate mentally and with local tooling where available:

| Gate | Pass condition |
|---|---|
| Intent | A reader can tell what the code does from names and structure before reading every line |
| Scope | The change touches the smallest responsible surface and avoids unrelated cleanup |
| Boundaries | I/O, orchestration, domain policy, and presentation are not tangled without reason |
| Types | Data contracts are explicit enough for editor, compiler, or tests to catch misuse |
| Tests | The most likely regression has a focused test or a clearly stated verification gap |
| Errors | Failure modes are handled at the boundary that can add useful context |
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
   Run available tests, typechecks, linters, or focused helper scripts. Re-read the diff as if you were reviewing a stranger's code.

6. Report plainly.
   Explain what changed, why this shape is maintainable, what was verified, and what risk remains.

## Optional Helper

Use the helper as a fast smell scanner, not as a verdict:

```bash
python3 scripts/analyze_maintainability.py /path/to/project
python3 scripts/analyze_maintainability.py /path/to/project --json
```

Treat its output as prompts for human review. A quiet script does not prove code is good, and a noisy script does not prove code is bad.

## Reading Guide

| Need | Read |
|---|---|
| Principles behind the defaults | `references/principles.md` |
| Splitting functions, modules, and responsibilities | `references/decomposition.md` |
| Review findings and severity ordering | `references/review-rubric.md` |
| Plans for other agents or teammates | `references/implementation-plans.md` |
| Common traps and anti-patterns | `references/gotchas.md` |
| Source influence and adaptation notes | `references/source-notes.md` |

## Gotchas

1. Small functions are not automatically maintainable. Fragmentation can hide the story as badly as a long function.
2. DRY is not a command to merge coincidentally similar code. Shared code should share a reason to change.
3. "Clean" code can still be wrong. Preserve behavior and verify before polishing structure.
4. Generic abstractions often age worse than explicit duplication. Wait for real variation.
5. Comments cannot rescue misleading names or tangled boundaries. Rename or restructure first.
6. Agent-generated code often passes tests while violating local idioms. Match the repo before applying global advice.
