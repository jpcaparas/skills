---
name: skill-creator-advanced
description: "Create, harden, and curate production-grade installable skills and skill libraries. Use for API/CLI/reference skills, invocation design, progressive disclosure, evals, placement, promotion, renames, deprecation, or catalog/router consistency. Skip trivial one-file utilities."
---

# Advanced Skill Creator

Creates and curates production skills whose process is predictable, evidence-backed, portable, and safe to release. Predictability means following the same sound decision path each run, not forcing identical wording or output.

Use the installed `skill-creator` skill for a small utility or simple workflow that does not need a release-grade research, curation, and eval loop. If that skill is unavailable, apply its documented lightweight workflow or create the minimal package directly.

## Route the Work

```text
What is changing?

├── One small, focused skill with little operational risk
│   └── Use the installed skill-creator skill when available
│
├── A new or existing API, CLI, SDK, or large reference skill
│   └── Follow Phases 0–7 below
│
├── A skill collection: create, improve, merge, compose, promote, move, deprecate, retire, or remove
│   └── Read references/curation.md first, then follow the applicable phases
│
└── An existing production skill with weak triggering, disclosure, or verification
    └── Inventory it completely, preserve proven behavior, then harden it in place
```

## Quick Reference

| Need | Read or run |
|---|---|
| Decide an ownership or lifecycle action | `references/curation.md` |
| Choose destination | `references/placement.md` or `scripts/infer_destination.py` |
| Regression-test destination inference | `python3 scripts/test_infer_destination.py` |
| Design earned package structure | `references/anatomy.md` |
| Choose disclosure, granularity, and specificity | `references/patterns.md` |
| Use an API, CLI, or reference blueprint | `references/blueprints.md` and the matching template |
| Design behavioral and trigger evals | `references/testing.md` |
| Curate feedback without accumulating stale rules | `references/self-improvement.md` |
| Validate a draft | `python3 scripts/validate.py <skill-path> --profile draft` |
| Validate a release | `python3 scripts/validate.py <skill-path> --profile release` |
| Run structural eval preflight | `python3 scripts/test_skill.py <skill-path>` |

## Phase 0: Intake and Ownership

Inspect the request, current repository, installed skill family, and local instructions before asking questions. Skip decisions that supplied context or repository evidence already settles. Ask only when one unresolved choice would materially change the result; confirm only an irreversible or genuinely ambiguous action.

1. Inventory adjacent skills and choose the applicable ownership or lifecycle action. Read `references/curation.md` when a library or neighboring skill is in scope.
2. Identify every distinct invocation branch and its current or proposed owner.
3. Determine who must reach the skill—agent, human, another skill, or a router—and verify how the target harness represents that contract.
4. Determine the destination:
   - An explicit user path wins.
   - Otherwise inspect established repo-local and global roots with `scripts/infer_destination.py`.
   - Prefer an existing repo convention over a generic fallback.
5. Classify the work:

| Blueprint | Use when | Starting point |
|---|---|---|
| API Wrapper | External API or SDK operations need exact auth and request contracts | `templates/api-wrapper/` |
| CLI Tool | A command-line surface needs verified commands, flags, and output handling | `templates/cli-tool/` |
| Progressive Docs | Several branches need navigable reference without loading every topic | `templates/progressive-docs/` |
| Library Curation | Existing skills or publication surfaces are changing | `references/curation.md` |
| Custom | None of the above fits | `references/anatomy.md` |

Before scaffolding a new skill, tell the user the inferred destination and concise reason. Keep that author-time recommendation out of the generated package.

**Phase complete when:** the destination, lifecycle decision, invocation branches, owner, and blueprint are recorded, and every material choice is resolved or explicitly bounded so later work cannot silently choose a different outcome.

## Phase 1: Research and Evidence

Gather ground truth before writing behavior.

### API or SDK

- Read current primary documentation for auth, versioning, operations, pagination, errors, quotas, pricing, and destructive effects.
- Map each claimed operation to evidence. Mark anything unresolved rather than guessing.
- Verify with the safest useful rung: static syntax → documented contract → dry run or sandbox → read-only live call.
- Do not perform writes, sends, purchases, production mutations, or credential-dependent effects without authority already present in the user's request.

### CLI

- Capture the installed version or build identity and the tool's documented help or command-introspection output for the root and relevant subcommands.
- Map commands, options or parameters, defaults, output or result formats, completion or exit semantics, environment constraints, and mutation boundaries.
- Prefer a documented preview or dry-run facility, a temporary workspace, or a disposable sandbox for operational checks.

### Progressive Reference

- Map user goals and branches before mapping products or files.
- Identify shared prerequisites and branch-only knowledge.
- Estimate likely access patterns; raw line count is only a pressure signal.

### Existing Skill or Library

- Read the complete canonical package and relevant repo policy: `SKILL.md`, references, scripts, templates, evals, assets, agents, wrappers, catalogs, registries, routers, and dependents.
- Before the first write, preserve a recoverable baseline outside the target package: record an immutable version-control revision and working-tree state, or copy an unversioned package into the evaluation workspace. Stop if the old behavior cannot be recovered for comparison.
- Run baseline validation and record current failures.
- Account for every existing behavior as preserved, changed, merged, or intentionally removed.
- Find duplicated rules, stale surfaces, unresolved placeholders, weak pointers, and filler structure.

**Phase complete when:** every retained factual or operational claim has evidence, a safe verification plan, or an explicit unresolved limitation; every existing behavior in scope is accounted for; and an improvement has a recoverable pre-write baseline.

## Phase 2: Architecture

Read `references/anatomy.md` and `references/patterns.md`. Build a branch-and-content ledger before creating files.

### Earn Each Artifact

Only `SKILL.md` is universally required. A production release also needs meaningful evals. Add support artifacts because they carry behavior:

| Artifact | Earn it when |
|---|---|
| `references/` | Some branches need detail that other branches should not load |
| `scripts/` | Work is deterministic, repeated, or safer as executable validation |
| `templates/` | Consumers copy and customize a stable starter |
| `assets/` | Static resources are used in generated output |
| `agents/` | A supported harness benefits from an independently scoped role |
| thin wrappers | Repository presentation or registry policy requires them |

Do not manufacture empty directories or placeholder references. Keep `SKILL.md` authoritative; wrappers orient humans or registries without copying the runbook.

### Design the Information Hierarchy

1. Keep ordered, always-needed steps in `SKILL.md`.
2. Keep compact always-needed rules beside the steps they govern.
3. Move branch-only reference behind a context pointer that says **when to read it** and **what decision or action it supports**.
4. Put deterministic repetition in scripts and copyable starting material in templates.
5. Omit advice the target agent already follows reliably without the skill.

Inline must-have material used by every branch. Co-locate each concept's rule, caveat, and example. Split a skill when a job needs independent invocation or when a real context boundary fixes observed early completion; do not split only because a line threshold was crossed.

### Define Frontmatter and Invocation

Use portable `name` and `description` fields by default. Apply harness-specific invocation controls only after reading that harness's current contract.

For a discoverable description:

- front-load the defining action or domain
- represent each distinct invocation branch once
- collapse synonym-only trigger lists
- state adjacent-use boundaries positively
- add explicit exclusions only for realistic near-misses demonstrated by evals
- keep implementation details in the body

### Define Completion Criteria

End every procedural phase or step with an observable criterion. Make it exhaustive where thin coverage is the likely failure: “every governed surface reconciled” is stronger than “update documentation.”

**Phase complete when:** every branch, content item, dependency, completion criterion, and publication surface has one deliberate location or documented omission.

## Phase 3: Write and Prune

Write the smallest package that reliably changes behavior.

- Use an early decision tree only when branches genuinely need disambiguation.
- Add a quick-reference table only when repeated operations benefit from scanning.
- Document gotchas that are non-obvious and evidenced; do not invent a quota.
- Keep working examples syntactically valid and match specificity to fragility.
- Use imperative instructions and explain load-bearing reasons.
- State the desired behavior first. Retain prohibitions for real safety, integrity, or scope guardrails and pair them with the permitted action.
- Keep each meaning in one canonical place. Replace copies with conditional pointers.
- Prefer current official sources for unstable technical claims, but keep creation history out of runtime instructions.

Then run the canonical sentence-level pruning pass in `references/curation.md`. Record what was deleted, merged, moved behind disclosure, or retained as an intentional choice; use comparative evals when a suspected no-op is disputed.

Use the five-file domain layout from `references/patterns.md` only when that access pattern is genuinely useful; it is an optional blueprint, not a universal requirement.

**Phase complete when:** every retained sentence has a declared role—behavior, load-bearing rationale, or necessary routing—while disputed no-op guidance is resolved with comparative evidence; no placeholder or duplicate canonical rule remains.

## Phase 4: Verify Safely

Verification is part of completion, not an optional follow-up.

1. Run the packaged release validator when Python 3.10 or newer is available:

   ```bash
   python3 /path/to/skill-creator-advanced/scripts/validate.py <skill-path> --profile release
   ```

   Extended YAML frontmatter and live YAML manifests also require PyYAML or the target harness's strict schema tooling. When the runtime or parser is unavailable, apply the same release gates with repository-native tooling or a manual audit and report that the packaged validator was not executed; do not translate a missing validator capability into a passing result.

2. Verify every example at the safest applicable rung:
   - parse or syntax-check code without executing unsafe behavior
   - confirm commands, options, defaults, and versions against current primary help or introspection output
   - use dry runs, temporary directories, sandboxes, or read-only calls
   - execute external mutations only when authorized and scoped
3. Verify all local pointers and eval fixtures remain inside the package and resolve.
4. Verify every description branch has realistic positive and near-miss trigger coverage.
5. For library changes, reconcile every governed catalog, registry, router, wrapper, installer, dependent, and lifecycle state from the affected-surface ledger.
6. Run the repository's fresh discovery or install-list command when one exists.

Record evidence and limitations honestly. A structural checker cannot substitute for behavioral evals, and a blocked live call is not a verified call.

**Phase complete when:** every claimed behavior and publication surface has passing evidence or an explicit limitation, with no unauthorized effect used to obtain it.

## Phase 5: Test Behavior and Invocation

Read `references/testing.md`. Save realistic cases in `<skill-name>/evals/evals.json` with unique IDs, concrete prompts, expected outcomes, typed assertions, and any committed fixtures.

Keep invocation queries in a separate trigger-eval file using the target runner's `query` and `should_trigger` contract. Do not feed behavioral cases to a trigger-only runner or treat structural preflight as either result.

Cover applicable categories:

| Category | Proves |
|---|---|
| Smoke | The primary branch works end to end |
| Edge | A boundary or unusual input does not collapse the process |
| Negative | A near-miss routes elsewhere or an unsafe request is bounded correctly |
| Disclosure | A captured tool trace proves the relevant file loaded and unrelated material did not, or observable branch-specific consequences prove the distinction |
| Invocation | Implicit positive and adjacent negative prompts trigger accurately |
| Curation | Every applicable ownership and lifecycle transition reconciles governed surfaces |

Follow the paired with-skill/baseline behavioral workflow supplied by the installed `skill-creator` package when available. Its `run_eval` command is for trigger queries, not behavioral output grading. Locate the package through the current harness or installation root rather than assuming a machine-specific path. Use this package's lightweight script only as structural preflight:

```bash
python3 /path/to/skill-creator-advanced/scripts/test_skill.py <skill-path>
```

Compare runs with and without the skill. An assertion that passes equally well without it may expose a no-op instruction. Repeat stochastic evals enough to distinguish a stable process improvement from luck.

**Phase complete when:** every applicable branch and meaningful near-miss is covered, all structural preflight checks pass, behavioral evals pass, and failures are either fixed or explicitly accepted by the user.

## Phase 6: Curate Feedback and Lifecycle

Read `references/self-improvement.md` and `references/curation.md` when feedback or library state changes.

1. Fix the current target first.
2. Classify the cause: structure, content, disclosure, verification, invocation, lifecycle, or style.
3. Find the canonical existing rule before proposing another.
4. Promote a general lesson only when repeated evidence or a failing eval shows it changes behavior beyond one case.
5. Merge nuance into the canonical rule; remove contradicted, duplicated, stale, and no-op wording.
6. Add or strengthen the eval that proves the lesson.
7. Modify this creator's own canonical source only when it is explicitly in scope; otherwise report the candidate lesson without silently persisting it.

For every ownership or lifecycle transition—including create, improve, merge, compose, promote, rename or move, deprecate, retire, and remove—update every governed derived surface atomically and search for stale names afterward.

**Phase complete when:** the target is fixed, the evidence-backed lesson has one canonical home, superseded guidance is removed, affected surfaces agree, and regression evals pass.

## Phase 7: Portability and Handoff

Read `references/cross-harness.md` for the target platforms.

- Keep the core useful with only portable `SKILL.md` behavior.
- Treat scripts, subagents, UI metadata, invocation controls, and auto-loading as harness capabilities to verify, not universal guarantees.
- Express skill and agent dependencies through primitives the publishing system documents. When symbolic references are unsupported, use literal installed names, repository dependency metadata, or inline the required portable behavior. Use relative literal paths for files inside the package.
- Choose a runtime guaranteed by the target environment. Follow that runtime's portable launcher and dependency conventions, prefer built-in facilities where practical, emit structured output when machines consume it, document exit semantics, and avoid machine-specific paths.
- Distinguish hard dependencies from soft enhancements. Surface required setup only when the skill would otherwise be wrong; let optional context degrade gracefully.

**Phase complete when:** the package works on the promised harnesses, platform-specific enhancements are capability-gated, discovery succeeds, and the handoff names verification evidence plus any remaining limitation.

## Gotchas

1. A scaffold is a draft, not a release; unresolved placeholders and empty evals must fail release validation.
2. Pointer existence does not prove disclosure. Test that the right branch loads the file and an unrelated branch does not.
3. More keywords can reduce invocation precision. Cover branches once and let trigger evals justify exclusions.
4. Append-only feedback creates sediment. Merge, replace, and delete before adding a rule.
5. Catalogs and routers are derived state. Make consistency executable where the repository repeats the rule.
6. The bundled scaffold publishes only when the host and destination filesystem expose an atomic no-replace directory move. If it reports partial certification or unsupported publication, create the earned files through repository-native tooling and apply the same validation gates; do not weaken no-clobber semantics.

## Reference Files

Read only the files the current branch needs:

| File | When to read |
|---|---|
| `references/curation.md` | Choosing create, improve, merge, compose, promote, rename, deprecate, remove, invocation ownership, or publication surfaces |
| `references/anatomy.md` | Assigning behavior to `SKILL.md` and earned support artifacts |
| `references/placement.md` | Choosing a repo-local or global destination |
| `references/patterns.md` | Designing disclosure, context pointers, co-location, granularity, and freedom |
| `references/blueprints.md` | Applying an API, CLI, progressive-reference, or curation blueprint |
| `references/testing.md` | Designing behavioral, trigger, disclosure, differential, and safety evals |
| `references/self-improvement.md` | Converting feedback into evidence-backed canonical rules |
| `references/cross-harness.md` | Verifying portability and harness-specific capabilities |
| `references/gotchas.md` | Diagnosing non-obvious authoring failures after the relevant phase is known |

## Agent Instructions

| File | When to use |
|---|---|
| `agents/reviewer.md` | Independently audit the release gate, evidence, disclosure, and lifecycle consistency |
| `agents/improver.md` | Diagnose feedback, propose minimal changes, and identify what should be pruned |
