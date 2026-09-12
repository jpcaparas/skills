# Gotchas — Skill Authoring Failure Modes

Use this catalog after the relevant branch is known. It contains non-obvious failure modes; canonical process rules live in `SKILL.md` and the focused references.

## Structure and Ownership

- **Scaffold mistaken for release** — generated folders, placeholders, and an empty eval file prove only that a draft exists. Release validation must reject unresolved work.
- **Empty structure as status** — `.gitkeep` trees, placeholder references, and forced sections add maintenance surface without behavior. Earn each artifact from the branch/content ledger.
- **New skill without a new owner** — another package already owns the same trigger and process. Improve or merge unless the branch needs independent invocation.
- **Multiple canonical homes** — wrappers, templates, and references repeat the runbook. Keep behavior in one place and derive or validate projections.
- **Router drift** — a router names removed skills or misses current ones. Treat it as a governed publication surface and audit it on every lifecycle change.

## Invocation and Disclosure

- **Synonym-heavy description** — repeated keywords rename one branch and increase permanent context load. Represent each real branch once.
- **Catch-all scope** — phrases such as “for anything related to X” overtrigger. State the actual job and add near-miss evals.
- **Universal exclusions** — long prohibition lists activate adjacent tasks and crowd out the positive target. Add explicit exclusions only when trigger evidence needs them.
- **Bare pointer** — a path exists but its wording does not tell the agent when to open it or what to do with it. Encode condition, purpose, and target.
- **Hidden invariant** — every branch needs a rule that was pushed behind optional disclosure. Keep shared must-have material inline.
- **Reference maze** — one answer requires chasing several accidental hops. Route directly from the earliest context that knows the condition.
- **Furniture without a branch** — a linear or reference-only skill gains an invented decision tree, table, or gotcha quota. Use only structures that improve access.

## Process and Completion

- **Activity without a gate** — “review,” “research,” and “test” let the agent move on early. End each phase with checkable evidence and exhaustive accounting where partial work is dangerous.
- **Size-driven split** — line count alone produces several skills with competing triggers. Disclose branch-only content first; split for independent invocation or a useful context boundary.
- **Implicit choice** — an omitted decision is neither intentional freedom nor a routed branch. Name the choice or state why the model may decide it.
- **Question-first intake** — the skill asks for information already present in the request or repository. Inspect first and ask only when a material branch remains unresolved.

## Verification and Safety

- **Schema pass presented as behavioral proof** — structural preflight cannot show that prompts trigger correctly or that instructions improve behavior. Run behavioral evals before release.
- **Broken evaluator scored as skill failure** — missing authentication, undiscovered temporary skills, or swallowed subprocess errors can make every positive return false. Health-probe the evaluator and separate infrastructure failures from model behavior.
- **Live-first verification** — testing a write, send, purchase, or production mutation creates risk merely to prove syntax. Climb from parsing and docs through dry run/sandbox/read-only calls, and require authority for external effects.
- **Plausible but wrong evidence** — a command returns zero while the assertion checks the wrong path, type, or surface. Trace the promised behavior to its exact observable.
- **Unpinned unstable fact** — an endpoint, flag, rate limit, model ID, or harness capability drifts. Cite current primary evidence and record a revalidation path.
- **Unsupported portability claim** — scripts, subagents, manual invocation controls, or auto-loading are treated as universal. Capability-gate them and keep the portable core useful.

## Feedback and Curation

- **Append-only learning** — every correction adds a dated rule and none leaves. Fix locally, merge proven nuance into one canonical rule, then prune superseded text.
- **One-off promoted as doctrine** — a vendor fact or user preference becomes a global authoring rule. Require repeated independent evidence or a discriminating eval.
- **No-op instruction** — prose sounds relevant but the model behaves the same without it. Compare against a baseline and delete behavior-neutral text.
- **Sediment preserved in runtime guidance** — change history, stale versions, resolved TODOs, and retired exceptions remain loaded. Keep provenance in version control or release notes.
- **Partial lifecycle update** — canonical skill changes while catalog, registry, router, wrapper, installer, or dependents remain stale. Reconcile the affected-surface ledger atomically.
- **Checklist-only consistency** — repeated publication rules drift because nothing executes them. Add a repo-native inventory check when the mapping is deterministic.
- **Silent self-modification** — feedback about a target skill mutates an installed creator copy without authority or a canonical source checkout. Report the candidate lesson unless the creator itself is in scope.

## Writing and Examples

- **Positive target missing** — a prohibition names the unwanted behavior but never says what to do. Lead with the desired action; retain hard safety guardrails and pair them with the safe alternative.
- **Pseudocode disguised as copyable code** — placeholders look executable and fail when copied. Mark drafts clearly and verify release examples.
- **General knowledge crowds out domain knowledge** — the skill explains programming basics instead of the unstable contract, exceptions, and decisions the agent lacks.
- **Thin wrappers become alternate instructions** — public `README.md`, `AGENTS.md`, or metadata files drift into a second runbook. Keep them short and point to canonical `SKILL.md`.

## See Also

- `references/curation.md` — ownership, lifecycle, affected surfaces, and pruning
- `references/patterns.md` — branch ledgers, pointers, completion criteria, and granularity
- `references/testing.md` — behavioral proof and safe verification ladders
- `references/self-improvement.md` — evidence thresholds for reusable lessons
