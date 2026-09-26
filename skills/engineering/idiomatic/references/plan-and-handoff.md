# A plan people can approve and agents can resume

Use this when presenting an alignment plan. Scale the detail to the scope and uncertainty, not to a fixed report length. The stakeholder decision should be understandable without reading implementation notes; the implementer should have enough evidence to start without rediscovering the entire project.

## Put the decision first

Start with the recommendation, the observed problem it addresses, the smallest useful first commitment and what stays unchanged. Translate mechanisms into consequences: “move vendor response interpretation behind one tested adapter” explains how risk decreases; “apply clean architecture” does not.

Explain why the sequence is preferable to the credible alternatives, including leaving the code alone. Name disruption, residual risks, organisational dependencies and the evidence that would change the recommendation. Do not promise savings, incident reductions or deadlines unsupported by measurements and capacity. Give estimate ranges with assumptions, or call for a time-boxed discovery step when uncertainty dominates.

Use layered detail:

- **Decision brief:** outcome, recommendation, expected benefit versus measured benefit, scope, tradeoffs and approval requested.
- **Evidence and target:** coverage map, consequential findings and preserved exceptions, current-to-proposed responsibilities and version-applicable sources.
- **Phased delivery:** stable phase IDs, dependencies, concrete actions and the phase contract from `SKILL.md`. Expand the next executable phase; keep uncertain later phases conditional.
- **Technical appendix:** evidence anchors, tests/check commands, unresolved facts and the continuation prompt below.

These are content needs, not compulsory headings. A small library may need a few paragraphs rather than a programme. A workspace-wide enterprise plan needs coverage across its applications, not merely its most obvious controller. Keep coverage and later phases compact; detail is earned by a current decision or execution need. Shared invariants, authority limits and verification rules belong once in the human plan, with phase-specific exceptions beside the phase. Defer speculative command designs and test matrices rather than filling every later phase with them.

## Make claims auditable

Give findings stable IDs and distinguish observation, interpretation and proposal. For each material change, link:

`local evidence → applicable contract/convention → actual consequence → proposed change → deciding check`

Use repository-relative paths and symbols or revision-qualified anchors that survive copying. Mark proposed files as proposed. For external claims, cite the source, relevant section and applicable version; a generic documentation homepage does not substantiate a disputed recommendation. If runtime/deployed versions are unknown, say so.

Keep source details proportionate: enough to verify the decision without pasting private payloads, whole files or documentation dumps. Preserve the distinction between performed checks, planned checks and unavailable evidence. Do not report a test command as passing merely because it exists in configuration.

Make progress observable. Useful measures might include incidents attributable to a boundary, change lead time, distinct duplicated rules, public-contract regressions or one representative task's before/after effort. Choose measures the project can actually collect; a speculative token-saving estimate is not a business case.

## Make every stopping point viable

Each phase must leave a state the team can live with if the next phase never happens. Name remaining compatibility bridges, supported old/new versions and the cost of stopping there. If a phase cannot ship alone, say that and identify its atomic deployment group instead of pretending the steps are independently releasable.

Separate local acceptance, release readiness and production acceptance. Specify the relevant evidence for each; do not bury migration or restart authority in “run the checks”. State where a failed test, unexpected record count, old worker version or missing approval stops dependent work.

For part-time work, include the next smallest safe slice and its prerequisite checks rather than a large unfinished move. Record checkpoints after coherent slices: phase/finding IDs, base/current revisions, dirty files, checks/results, decisions, remaining temporary tools and next action. Use the repository's existing plan or ticket location if one exists; otherwise a copy-pastable checkpoint in the reply is enough.

## End endorsement-first plans with an agent continuation prompt

Fill this example with the actual plan and evidence; omit irrelevant fields rather than leaving placeholders. The user should be able to paste it into a fresh session that has never seen the conversation. Include the selected phase's necessary content inline; referencing a plan file is sufficient only if that file actually exists and will be accessible to the next session. Include only the evidence needed to start that slice and a compact list of later phase IDs/outcomes. Do not duplicate the full coverage map, every finding or deferred operational recipes. Self-contained means sufficient to resume safely, not an archive of the entire assessment.

```text
Use idiomatic if available; the instructions below are sufficient without it.

Outcome and workspace: [repository/project, applications, desired outcome].
Mode and authority: [plan only, or the specific approved implementation scope].
This handoff does not itself grant approval. Confirm that the current user has
authorised implementation; if not, review the plan and request that decision.
Production reads: [allowed environment/data scope, or not authorised].
Production writes, deployment, publishing and external spending:
[specific existing approval and conditions, or not authorised].

Baseline: [revision, dirty work, framework/library/runtime versions and unknowns].
Evidence: [relevant files/symbols, versioned primary sources and observed facts].
Preserve: [public behaviour, domain/integration quirks, valid local conventions].
Do not change: [explicit exclusions, unrelated work and deferred decisions].

Plan: [stable phase IDs, outcomes, dependency order and current status].
Next slice: [selected phase ID, concrete changes/proposed paths and why first].
Prerequisites: [harness, data facts, compatibility checks and owner decisions].
Acceptance: [observable results and exact verified/proposed check commands].
Recovery and pause state: [rollback/forward limits and remaining bridges/tools].
Stop if: [failed gates, materially changed evidence, data or authority].

First action: inspect project guidance and current worktree, compare with this
baseline, read the named files, and recheck the prerequisites before editing.
Do not assume the old deployed state, approvals or test results still apply.
Proceed within confirmed authority; report evidence and update the checkpoint.
```

Do not embed secrets, customer records or credentials in this prompt. Do not carry a blanket “fully autonomous” instruction across an unbounded scope. A plan endorsement and a production-write approval are separate decisions. During same-session execution, use a shorter checkpoint at a pause rather than repeatedly printing the whole plan.
