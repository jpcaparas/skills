# Skill Authoring and Library Curation

Use this reference for skill ownership and lifecycle changes. Preserve the required outcomes and safety boundaries; investigation order, working notes, and presentation can vary with the task.

## Table of Contents

- [Start With the Existing System](#start-with-the-existing-system)
- [Choose Create, Improve, Merge, Compose, or Retire](#choose-create-improve-merge-compose-or-retire)
- [Define the Invocation Contract](#define-the-invocation-contract)
- [Build a Branch and Content Ledger](#build-a-branch-and-content-ledger)
- [Use Checkable Completion Criteria](#use-checkable-completion-criteria)
- [Model the Library Lifecycle](#model-the-library-lifecycle)
- [Reconcile Publication Surfaces](#reconcile-publication-surfaces)
- [Separate Reusable Behavior From Local Configuration](#separate-reusable-behavior-from-local-configuration)
- [Prune Before Adding](#prune-before-adding)
- [Make Consistency Executable](#make-consistency-executable)
- [Release Gate](#release-gate)

## Start With the Existing System

Inspect before proposing structure. Repository conventions outrank this reference when they are explicit and internally consistent.

Inventory the affected surfaces. A collection-wide reorganization needs the whole map; a local repair needs its behavior and consumers, not an unrelated documentation census:

- every canonical `SKILL.md` and its invocation description
- adjacent skills with overlapping jobs, inputs, or trigger language
- the repository's draft, published, private, and retired states
- catalogs, manifests, registries, installer lists, generated docs, and discovery commands
- router or setup skills that name other skills
- thin wrappers such as `README.md`, `AGENTS.md`, and metadata files
- tests, evals, scripts, templates, and dependents
- local instructions governing naming, placement, promotion, or deprecation

Skip questions that this evidence already answers. Ask only when an unresolved choice would materially change the result, and lead with the best-supported recommendation.

Complete this inspection when every existing skill and governed publication surface in scope is accounted for.

## Choose Create, Improve, Merge, Compose, or Retire

Do not assume a new request deserves a new skill.

| Decision | Choose it when |
|---|---|
| Improve | An existing skill owns the same invocation branch and needs clearer behavior, evidence, or disclosure |
| Merge | Two skills compete for the same trigger and follow substantially the same process |
| Create | The branch has an independently useful job, recognizable vocabulary, and a reason to be reached on its own |
| Compose | Separate jobs must remain independently reachable but share a stable prerequisite or reference |
| Retire | The behavior is obsolete, superseded, unused, or harmful, and dependents can be migrated |

Line count alone does not justify a new skill. A long cohesive reference can stay together behind good disclosure; a shorter package may need splitting when it contains independently invoked jobs.

Record the decision and the evidence that distinguishes the chosen branch from its nearest neighbor. If the distinction cannot be stated clearly, improve or merge instead of creating.

## Define the Invocation Contract

Determine who or what must be able to reach the skill:

- autonomous agent discovery
- explicit human invocation
- another skill or workflow
- a repository-specific router or catalog

Then verify how the target harness represents that contract. Invocation-only fields and slash-command behavior are platform capabilities, not portable assumptions. Keep universally valid `name` and `description` frontmatter unless the target's documented contract explicitly supports another mode.

For discoverable skills, apply the description rules in `SKILL.md` under Define Frontmatter and Invocation. Each primary job needs a clear owner; compatible supporting skills can compose without pretending all overlap is a conflict. Make precedence clear where neighboring skills could compete for the same request.

Explicit-only skills trade agent discoverability for human memory. When many accumulate, a router can reduce that memory burden, but the router is a derived surface: it must be rechecked whenever a reachable skill changes.

Complete this decision when every invocation branch has one owner and the target harness can actually enforce the intended reachability.

## Build a Branch and Content Ledger

For a multi-package change, a branch-and-artifact ledger can track current and proposed owners, lifecycle state, dependents, and affected publication surfaces. Use a smaller note or the diff for a simple change; the requirement is not to lose a behavior or consumer, not to produce a particular document.

A strong context pointer says both when to load a file and what decision or action it supports:

> Read `references/cross-harness.md` when target-specific invocation controls are in scope; use it to select and verify a supported invocation contract.

Keep must-have material inline if every branch needs it or repeated disclosure tests show the pointer is unreliable. Co-locate a concept's rule, caveat, and example so the agent does not assemble one decision from scattered fragments.

Complete the ledger when every retained statement has one canonical location and every branch can reach all—and only—the material it needs.

## Use Checkable Completion Criteria

Define observable completion for the outcome and consequential handoffs. Intermediate gates are useful where partial work is dangerous, not as mandatory furniture after every step. Prefer criteria that are:

- **checkable** — the agent can distinguish done from not done
- **exhaustive where needed** — every affected branch, artifact, or claim is accounted for
- **behavioral** — they describe evidence, not activity

Weak: “Review the existing skill.”

Strong: “Every existing behavior is marked preserved, changed, merged, or intentionally removed, with its canonical file named.”

Sharpen a completion criterion before splitting a workflow merely to hide later phases. Split by sequence only when a genuinely fuzzy phase repeatedly ends early and a real context boundary improves the behavior.

## Model the Library Lifecycle

Discover the repository's own states rather than imposing folder names. A useful lifecycle usually distinguishes at least:

- work that is still experimental or private
- work actively published or discoverable
- work retired but retained for history or migration

Treat composition, promotion, rename, move, deprecation, and removal as governed changes with explicit entry and exit criteria.

### Composition

Compose only when each job must remain independently reachable and the shared prerequisite or reference is stable enough to own separately. Before composing, prove that each child has a distinct invocation owner, choose a dependency mechanism the target harness or repository actually supports, and add a portable plain-language prerequisite when symbolic references are unavailable. Composition passes its gate when every child is independently discoverable, dependency resolution is verified, shared changes revalidate all dependents, and no child competes with the shared package for the same trigger. If consumers cannot resolve the dependency reliably, keep the shared requirement inline instead.

### Promotion

Promote only when the skill passes its release validation, behavioral evals, discovery check, and every required publication surface includes it. Draft material stays out of active catalogs and installers unless repository policy says otherwise.

### Rename or Move

Update canonical paths, dependents, catalogs, registries, routers, docs, tests, and installer discovery together. Search for the old name after the move; no stale active route should survive.

### Deprecation or Retirement

Name the replacement when one exists, migrate dependents, remove the skill from active discovery surfaces, and preserve history only where repository policy expects it.

### Removal

Remove a retired package only after the repository's retention rule is satisfied, active dependents and routes are absent, and policy permits deleting the retained history. Re-run dependency and discovery checks after deletion; an old scan is entry evidence, not proof of the final state.

## Reconcile Publication Surfaces

Build an affected-surface ledger before editing:

| Surface | Question |
|---|---|
| Canonical skill | Is `SKILL.md` still the single behavioral source of truth? |
| Catalog or README | Does the entry accurately orient a human without copying the runbook? |
| Registry or manifest | Does it include exactly the skills this lifecycle state publishes? |
| Router | Does each route point to a current, reachable owner? |
| Installer or discovery | Can a fresh consumer find the intended skill and exclude retired drafts? |
| Wrappers and docs | Do they reflect job, trigger boundary, prerequisites, observable success, and neighbors? |
| Dependents | Do references, setup requirements, and compositions still resolve? |
| Evals | Do trigger, disclosure, behavior, and near-miss cases match the new contract? |

Update these surfaces atomically. A canonical skill change is incomplete while a derived catalog, router, or registry still lies about it.

Keep wrappers thin. Human-facing docs orient and situate; they do not duplicate operational steps. Generate or validate derived surfaces when their format is regular enough.

## Separate Reusable Behavior From Local Configuration

Keep portable skill behavior independent from repository-specific choices such as issue trackers, labels, paths, or organizational vocabulary.

Distinguish dependencies:

- A **hard dependency** makes the skill wrong or nonfunctional when configuration is absent. Surface it explicitly and provide a setup route.
- A **soft dependency** improves precision but has a safe default or graceful degradation path. Do not burden every invocation with mandatory setup prose.

Setup workflows should inspect first, skip settled choices, recommend a supported default, preview meaningful writes, update owned blocks in place, and create configuration only for installed dependents that need it.

## Prune Before Adding

Run this pass sentence by sentence:

1. **Single source** — merge duplicate meanings into one canonical rule.
2. **Relevance** — remove content that no longer affects the skill's current job.
3. **No-op** — remove instructions the target model follows equally well without the skill; prove disputed cases with comparative evals.
4. **Sediment** — delete stale history markers, superseded advice, and append-only feedback residue from runtime guidance.
5. **Sprawl** — move branch-only reference behind a good pointer or split independently invoked jobs.
6. **Freedom** — state outcomes and safe authority; keep exact steps only for a fragile contract. Replace arbitrary quotas, fixed output shapes, mandatory doc stacks, and aesthetic bans with useful examples or remove them. Retain safety, integrity, and scope prohibitions.
7. **Implicit choices** — decide whether each omitted detail is intentional freedom, a routed branch, or an accidental gap delegated to model defaults.

Pruning is complete when retained guidance earns its cost. Do not require a sentence-by-sentence report unless requested or needed for a contested rule. When a skill has become less useful, compare the intended result with current unassisted behavior; deletion or retirement may be better than adding another rule.

## Make Consistency Executable

Checklist-only publication rules drift. When the repository repeats an inventory or synchronization rule, turn it into a deterministic check using its native tooling.

Useful checks include:

- canonical skill names and paths are unique
- frontmatter names match directories
- published skills appear in every governed catalog or registry
- draft and retired skills are absent from active discovery surfaces
- routers mention current reachable skills and no removed ones
- wrapper metadata matches canonical name, version, and short description
- every local pointer and eval fixture resolves inside the package
- a fresh installer or discovery command sees the intended set when the repository contract exposes one

Do not guess a universal catalog schema. Read the repository policy or accept a small explicit manifest, then validate that contract.

## Release Gate

Release or promote only when:

- the applicable create, improve, merge, compose, promote, rename/move, deprecate, retire, or remove decision is evidenced
- every invocation branch has one owner and realistic trigger/near-miss evals
- the requested result and consequential handoffs have checkable completion criteria
- branch-only content is disclosed through condition-and-purpose pointers
- every claim and example has verification evidence or an explicit limitation
- no unresolved placeholder, duplicate canonical rule, or stale route remains
- all governed publication surfaces and dependents are reconciled
- required release validation and discovery checks pass, and behavioral claims are supported by executed evals rather than structural preflight alone

Keep incomplete behavioral evidence visible. A reviewed local improvement with unrun model evals is not a behaviorally certified release. Do not block a harmless local correction on unrelated platform experiments, or disguise missing evidence as success.

## See Also

- `references/anatomy.md` — portable package anatomy and earned resources
- `references/patterns.md` — disclosure, granularity, and context-pointer patterns
- `references/testing.md` — trigger, disclosure, differential, and behavioral evals
- `references/self-improvement.md` — evidence-backed feedback curation
- `references/cross-harness.md` — harness-specific invocation and portability constraints
