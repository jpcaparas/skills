# Evidence-Backed Self-Improvement

Feedback is a curation signal, not permission to append permanent rules. Fix the current target first, then decide whether the lesson is local, duplicated, contradictory, or genuinely general.

## Table of Contents

- [Operating Contract](#operating-contract)
- [Classify the Failure](#classify-the-failure)
- [Decide Whether the Lesson Generalizes](#decide-whether-the-lesson-generalizes)
- [Choose the Canonical Home](#choose-the-canonical-home)
- [Merge, Replace, and Prune](#merge-replace-and-prune)
- [Prove the Improvement](#prove-the-improvement)
- [Optimize Invocation Descriptions](#optimize-invocation-descriptions)
- [When to Keep Feedback Local](#when-to-keep-feedback-local)
- [Completion Gate](#completion-gate)

## Operating Contract

When a user corrects a generated skill:

1. Apply the smallest correct fix to the target in scope.
2. Reproduce the failure or identify the missing observable.
3. Classify the cause.
4. Search the target and this creator's canonical rules for an existing owner.
5. Propose a reusable lesson only if evidence shows it applies beyond the one case.
6. Add or strengthen an eval that fails before the fix and passes after it.
7. Modify this creator's own source only when the user has placed that canonical package in scope.

If the creator is merely installed elsewhere, report the candidate lesson and its proposed canonical location. Do not silently edit an installed copy or append to unrelated repositories.

## Classify the Failure

| Class | Typical symptom | First repair |
|---|---|---|
| Structural | Behavior lives in the wrong artifact or empty scaffold obscures the package | Rebuild the branch/content ledger |
| Verification | Example, command, or claim has weak or false evidence | Add the safest applicable check and preserve limitations |
| Disclosure | Required material is hidden, unrelated material loads, or pointer wording is vague | Fix the condition-and-purpose pointer or inline shared material |
| Invocation | Skill fails to trigger, overtriggers, or competes with a neighbor | Clarify branch ownership and add positive/near-miss evals |
| Lifecycle | Catalog, registry, router, wrapper, or dependent disagrees with canonical state | Reconcile the affected-surface ledger atomically |
| Content | Domain fact is wrong, stale, or incomplete | Verify current primary evidence and correct the canonical fact |
| Style | Wording weakens execution without changing the intended behavior | State the positive target and prune no-op prose |

Classify the cause, not merely the visible complaint. “The agent did not open the file” may be a disclosure pointer problem, a target-harness limitation, or ignored clear guidance; test before choosing the fix.

## Decide Whether the Lesson Generalizes

Use this decision table:

| Evidence | Treatment |
|---|---|
| One vendor fact or user preference | Keep the fix local |
| Existing rule already covers it | Strengthen the eval or wording; do not add another rule |
| New evidence adds a caveat | Merge the caveat into the canonical rule |
| New evidence contradicts a rule | Resolve against current authoritative evidence and replace superseded text |
| Repeated independent failures or a discriminating eval reveal a class of mistake | Promote one general rule |
| Signal is ambiguous | Investigate or ask; do not persist it yet |

Repeated evidence does not mean repeated wording. Store one rule with the narrowest scope that explains every proven case.

## Choose the Canonical Home

Place the lesson according to how it changes behavior:

| Lesson | Canonical home |
|---|---|
| Needed by every invocation | `SKILL.md` near the step it governs |
| Needed only by a branch | The routed reference for that branch |
| Deterministic repeated check | A script plus a brief invocation pointer |
| Copyable starting material | A template |
| Non-obvious exception | The relevant gotchas section |
| Repository publication invariant | Repo policy plus an executable consistency check |
| One-off domain fact | The target skill, not this creator |

Repository history is the provenance record. Do not leave permanent `[NEW]` markers, dated append logs, or superseded variants in runtime guidance.

## Merge, Replace, and Prune

Run the canonical pruning pass in `references/curation.md`. For feedback specifically, also remove the superseded correction, keep local facts in the target package, and ensure the regression eval—not duplicated prose—preserves the lesson. Finish by confirming that a deletion did not reopen the reported failure or a neighboring branch.

## Prove the Improvement

For each accepted lesson:

1. Create a realistic failing prompt or fixture.
2. Capture the before behavior.
3. Make the smallest canonical change.
4. Run the same eval with the skill and, when useful, without it.
5. Confirm the target behavior improves and no neighboring branch regresses.
6. Repeat stochastic cases enough to establish process consistency.

A rule that does not improve a discriminating eval may be a no-op, an assertion problem, or a model-specific hypothesis. Keep it out of permanent guidance until the evidence is clearer.

## Optimize Invocation Descriptions

Optimize after the skill body and branch ownership stabilize.

### Query Set

Build a balanced set that covers:

- direct positives naming the domain or action
- implicit positives that need the skill without naming it
- every distinct invocation branch
- adjacent near-misses with shared vocabulary
- a competing skill that should win
- varied formality, terminology, and project contexts

Do not use obviously unrelated negatives; they inflate scores without testing the boundary.

### Iteration

1. Split queries into a tuning set and a held-out set.
2. Run multiple trials when the harness is stochastic.
3. Diagnose misses by branch rather than adding synonym lists.
4. Apply the canonical description rules in `SKILL.md` Phase 2 to the failing branch.
5. Choose the shortest candidate that preserves held-out accuracy without moving implementation detail into frontmatter.

If an available evaluator provides a description-optimization loop, use it with the current supported model identifier and record the exact command. Do not hard-code stale model names into the skill.

## When to Keep Feedback Local

Keep feedback out of this creator's canonical rules when it is:

- a vendor-specific endpoint, environment variable, or version fact
- a personal formatting or language preference
- already covered by an adequate rule
- too ambiguous to reproduce
- caused by a transient tool failure rather than skill behavior
- specific to a harness capability this skill does not universally promise
- unsupported by authority to modify the canonical creator package

If the same local class recurs independently, revisit it with evidence; recurrence may reveal a general rule.

## Completion Gate

Improvement is complete when:

- the current target is fixed
- the failure class and evidence are recorded
- the lesson is either deliberately local or has one canonical reusable home
- duplicated, contradicted, stale, and no-op wording is removed
- the regression eval fails before and passes after the change
- adjacent branches and publication surfaces remain consistent
- release validation and behavioral evals pass

## See Also

- `references/curation.md` — lifecycle, invocation ownership, and publication-surface reconciliation
- `references/testing.md` — discriminating, repeated, trigger, and disclosure evals
- `references/patterns.md` — branch-based placement and completion criteria
- `references/gotchas.md` — current non-obvious authoring failure catalog
