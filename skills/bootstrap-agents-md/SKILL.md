---
name: bootstrap-agents-md
description: "Inspect; create or replace AGENTS.md and CLAUDE.md."
---

# Bootstrap AGENTS.md

Create a concise, evidence-backed root `AGENTS.md` and a companion `CLAUDE.md` that imports it. Replace an existing root instruction file wholesale rather than treating inherited wording as correct by default.

## Output Contract

Produce exactly these repository-root artifacts unless the user asks for a wider instruction hierarchy:

- `AGENTS.md`: repository-wide truths, decision guardrails, and completion expectations that should survive routine project evolution.
- `CLAUDE.md`: exactly `@AGENTS.md` followed by one newline.

The generated `AGENTS.md` must not contain concrete paths, URLs, commands or binary names, dependency or package names, version numbers, machine-specific assumptions, or copied session history. Express project knowledge as stable concepts: purpose, architectural boundaries, domain invariants, change risks, validation expectations, and local decision principles.

## 1. Establish Scope and a Recoverable Baseline

1. Resolve the project root from repository or workspace evidence. Stop only when multiple plausible roots would produce materially different files.
2. Capture working-tree state before writing. Preserve unrelated changes and do not reformat or clean other files.
3. Read any existing root `AGENTS.md` and `CLAUDE.md` into a replacement ledger. Treat them only as evidence to compare later; do not inherit their wording, structure, or assumptions into the draft.
4. Find nested agent-instruction files and record their scope and precedence. Do not replace or delete them unless the user explicitly includes them.

This phase is complete when the root is unambiguous, pre-existing content is recoverable or recorded, unrelated changes are known, and every instruction file that could override the root is accounted for.

## 2. Inspect the Whole Project by Evidence Surface

Map the repository before drafting. “Whole project” means every meaningful architectural and operational surface is accounted for, not that generated, vendored, cached, or binary content is read byte by byte.

Inspect, when present:

- project purpose, contributor documentation, and durable design notes
- manifests and workspace metadata without copying their tool-specific syntax
- top-level modules, entry points, public boundaries, and domain vocabulary
- tests, fixtures, and the behaviors they document
- automation, delivery, schema, migration, security, and operational configuration
- background work, external boundaries, persistence, state transitions, and recovery paths
- recent changes or repeated review signals when local history is available
- generated, vendored, cache, artifact, and secret-bearing areas only enough to classify and exclude them

Maintain an evidence ledger with: candidate rule, supporting surfaces, confidence, durability, and whether it belongs in always-loaded root guidance. Prefer repeated code and test evidence over a lone example. Mark contradictions and omit unresolved guesses from the generated file.

This phase is complete when every meaningful surface is marked inspected, intentionally excluded, or absent, and each candidate project truth has evidence and a confidence level.

## 3. Select Only Durable Guidance

Keep a candidate rule only when all of these are true:

- it applies repository-wide and is useful in most coding sessions
- it changes agent behavior beyond competent defaults
- it is supported by project evidence or an explicit user requirement
- it remains useful if files move, tooling changes, or dependencies evolve
- a reader can tell whether the rule was followed

Prefer conceptual specificity over literal specificity. Describe responsibilities, boundaries, and invariants without freezing the current directory layout or toolchain. Omit transient commands, inventories, implementation trivia, speculative architecture, style preferences already enforced mechanically, and task-specific procedures better kept in tests, automation, or scoped guidance.

Use negative-first wording only for costly failure boundaries. Pair every prohibition with the permitted action, for example: do not bypass failing verification; fix the cause or report the blocked check and remaining risk. Lead ordinary guidance with the desired behavior.

This phase is complete when every retained rule has evidence, repository-wide scope, durable value, and a declared behavioral purpose, while every rejected candidate has a reason in the working ledger.

## 4. Draft for Attention and Autonomy

Keep `AGENTS.md` compact and easy to scan. Use normal Markdown headings and short bullets. Put the most consequential boundaries first and avoid repeated urgency, slogans, role-play, exhaustive tutorials, and contradictory qualifiers.

Use this earned section order, omitting a section that has no project evidence:

1. **Critical boundaries** — destructive changes, sources of truth, data and secret safety, user-owned work, and validation bypasses.
2. **Project shape** — purpose, stable architectural responsibilities, domain language, and non-obvious invariants.
3. **Working method** — inspect before editing, keep scope narrow, follow repeated local patterns, and preserve intent.
4. **Maintainability** — readable names, stable responsibility boundaries, strong contracts where supported, comments for rationale, and no speculative abstraction.
5. **Tests and verification** — behavior-focused tests, regression evidence, deterministic boundaries, and proportionate configured checks.
6. **Reliability and operations** — only when applicable; idempotency before retries, bounded failure handling, explicit state, recovery, degradation, and useful observability.
7. **Completion** — evidence run, limitations, risks, and a plain handoff.
8. **Instruction hygiene** — remove stale or conflicting guidance and move mechanically enforceable invariants into project automation.

Assume the agent has strong fundamentals but lacks project history. Give it room to choose implementation details from current evidence. Do not prescribe an abstraction, test shape, operational mechanism, or documentation volume when the project does not earn it.

This phase is complete when the draft is concise, non-conflicting, project-grounded, free of forbidden literal details, and each negative guardrail names the safe alternative.

## 5. Replace Atomically

1. Write the new root `AGENTS.md` as a clean replacement, not an append or a patchwork merge.
2. Write `CLAUDE.md` as exactly one import line with a trailing newline. Do not duplicate instructions or add tool-specific advice.
3. Re-read both files from disk and inspect the diff. Confirm that only the two authorized root files changed unless the user requested more.

If either write fails, do not claim partial success. Report which artifact changed and restore a consistent pair when safe.

This phase is complete when both files exist, the companion is exact, the root file is a clean replacement, and the diff contains no unrelated edits.

## 6. Validate Structure and Substance

Run `scripts/validate_agents_md.py` against the project when its runtime is available. Otherwise apply the same checks manually; the helper is an enhancement, not a hard dependency.

Then perform a semantic audit the script cannot prove:

- each project claim maps back to the evidence ledger
- no important rule merely restates a generic competent-agent default
- no rule conflicts with a more specific surviving instruction file
- test and reliability guidance is conditional on actual project risk
- prose guidance does not pretend to enforce what belongs in automated checks
- a junior developer with solid fundamentals can understand the intent without session context

Fix failures and re-run validation. Do not weaken the validator or delete a useful rule merely to obtain a pass; revise the wording while preserving the evidenced intent.

This phase is complete when deterministic validation passes or its manual equivalent is recorded, the semantic audit has no unsupported claim, and remaining limitations are explicit.

## 7. Explain the Replacement

When either prior root instruction file existed, end the session with an exhaustive replacement report. Group every old instruction or section from both files into one disposition:

- **superseded** — valid intent expressed more durably or clearly
- **removed as brittle** — tied to a path, command, dependency, version, tool, or transient layout
- **removed as redundant** — already enforced or obvious from the repository
- **removed as unsupported** — contradicted or not evidenced by the project
- **moved out of root scope** — useful only for a specialized area or procedure

Name the reason for every group and mention conflicts with surviving nested instructions. Do not say the old file was “inferior” without evidence; explain the concrete maintenance or instruction-following risk that justified replacement.

When a prior root `CLAUDE.md` existed, account for its instructions too. Explain which content was duplicated, tool-specific, stale, or better owned by the canonical root guidance before replacing it with the import-only companion.

Report the inspection surfaces, stable truths encoded, files written, validation evidence, and any intentionally omitted uncertainty. Do not include research URLs or authoring history in the generated project files.

This phase is complete when every prior instruction is accounted for and the user can audit why the replacement is safer, less brittle, and more autonomous.

## Maintenance Reference

Read `references/source-notes.md` only when maintaining this skill, rechecking the `CLAUDE.md` import convention, or revising its prompt-design rationale. It is research evidence, not runtime project guidance.
