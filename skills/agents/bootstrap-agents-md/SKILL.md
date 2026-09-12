---
name: bootstrap-agents-md
description: "Bootstrap or refresh root AGENTS.md and CLAUDE.md."
---

# Bootstrap AGENTS.md

Create the smallest root instruction set that gives capable coding agents project knowledge they cannot reliably infer for themselves. Keep hard contracts exact and leave implementation and presentation choices open when current repository evidence can guide them.

## Output Contract

Produce these repository-root artifacts unless the user asks for a wider instruction hierarchy:

- `AGENTS.md`: high-signal repository truths, boundaries, and validation expectations that earn space in persistent context.
- `CLAUDE.md`: exactly `@AGENTS.md` followed by one newline.

When replacing an existing root instruction file, write a coherent new file rather than appending to inherited wording. Preserve supported intent, not the old file's structure.

Exact commands, repository-relative paths, tool or dependency names, versions, and URLs may belong in `AGENTS.md` when their literal form changes agent behavior and repository evidence shows they are stable. Exclude secrets, machine-local absolute paths, copied session history, volatile inventories, and detail that a competent agent can recover cheaply from the repository.

## 1. Establish Scope and Baseline

1. Resolve the repository root from workspace evidence.
2. Capture the working-tree state and preserve unrelated changes.
3. Read existing root `AGENTS.md` and `CLAUDE.md` as evidence. Record material intent that must be preserved, changed, or removed.
4. Find nested instruction files and respect their narrower scope. Change them only when the user includes them.

Stop for clarification only when competing roots or instruction owners would produce materially different results.

**Complete when:** the target root, authorized files, existing material intent, nested precedence, and unrelated work are understood well enough to write without guessing.

## 2. Inspect Just Enough of the Project

Inspect the evidence that can reveal non-obvious root guidance: project purpose, durable architecture or domain language, public boundaries, tests, configured checks, delivery or migration risk, external effects, and repeated local conventions. Classify generated, vendored, cached, binary, and secret-bearing areas without loading their contents unnecessarily.

Scale inspection to the repository and task. Prefer repeated code, tests, automation, and maintained design records over a lone example. Resolve contradictions that affect a retained rule; omit uncertain claims that do not need to be in persistent context.

The goal is sufficient evidence for the final guidance, not a census of every file or a permanent authoring ledger.

**Complete when:** every proposed project-specific rule has evidence, and further inspection is unlikely to change the root guidance materially.

## 3. Decide What Earns Persistent Context

Keep a rule when it is project-wide, non-obvious, behavior-changing, supported, and durable enough to justify always-loaded attention. A rule can also earn inclusion when the user explicitly requires it or when an observed failure shows that capable models need the extra steering.

Calibrate specificity to consequence:

| Direction | Treatment |
|---|---|
| Hard contract | State exact syntax, scope, or prohibition when correctness, safety, compatibility, or the harness requires it. Pair costly-failure guardrails with the safe action. |
| Project heuristic | Explain the project-specific reason and desired outcome. Let the agent choose the mechanism from current evidence. |
| Open choice | Leave headings, order, implementation design, test shape, abstraction, and documentation volume to the agent unless the repository or user constrains them. |

Start with the minimal rule set. Add examples only when an exact form matters or a demonstrated ambiguity survives clear prose; examples of ordinary wording and layout can accidentally become templates.

Exclude generic competent-agent advice, repeated urgency, style preferences already enforced by tooling, transient procedures, speculative architecture, and duplicated source material. Move guarantees into automation when the repository can enforce them mechanically.

Treat the absence of a subsystem, dependency, or workflow as current state rather than a permanent prohibition unless project evidence or the user establishes that boundary deliberately.

**Complete when:** every retained instruction has a load-bearing reason, and every omitted choice is either recoverable from the repository or deliberately left to agent judgment.

## 4. Draft for the Project, Not a Template

Choose the structure that makes this repository's guidance easiest to use. A small project may need only a few rules. A complex service may earn separate treatment of domain invariants, operational risk, validation, or instruction precedence. Section names, order, and count are output choices rather than release requirements.

Write at the altitude between vague slogans and brittle implementation scripts. Name the project fact, why it matters, and the result to preserve. Use literal detail when abstraction would make the instruction less actionable; point to a narrower source when the detail is too volatile for root context.

**Complete when:** the draft is concise, project-specific, internally consistent, and leaves unearned decisions open.

## 5. Write and Verify the Pair

1. Write root `AGENTS.md` as the clean replacement or new file authorized by the user.
2. Write `CLAUDE.md` as the exact import line with a trailing newline.
3. Re-read both files and inspect the diff for unrelated changes.
4. Run `scripts/validate_agents_md.py` when Python is available. Treat its structural checks and review signals as aids, not proof of semantic quality.
5. Confirm each retained claim against repository evidence, check for conflicts with nested guidance, and remove anything that only restates capable-model defaults.

If the pair cannot be written consistently, report the partial state and restore consistency when safe. Do not claim a semantic pass from the validator alone.

**Complete when:** both files form a consistent pair, structural validation passes, and the semantic audit finds no unsupported or conflicting root rule.

## 6. Report Material Decisions

Summarize the evidence surfaces inspected, the high-signal truths retained, the files changed, validation performed, and unresolved uncertainty or risk. When prior instructions existed, account for material groups as preserved, reframed, removed, or moved to narrower ownership and explain why.

Use an exhaustive line-by-line replacement ledger only when the user asks for it or the previous instructions are safety-critical, contested, or too complex to audit by material groups.

## Maintenance Reference

Read `references/source-notes.md` when maintaining this skill, rechecking the `CLAUDE.md` import convention, or revising its context-design rationale. Keep research history out of generated project instructions.
