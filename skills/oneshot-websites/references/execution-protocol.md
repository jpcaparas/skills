# Autonomous One-Shot Execution Protocol

Use this reference when preparing runs, dispatching several experiments, adapting to harness capabilities, or recording a rerun.

## Meaning of One-Shot

One-shot means the coordinator gives one actual prompt to one fresh owning lead. The lead then has full agency to finish the experiment. It may use many model turns, tools, edits, tests, dependencies, and recursively delegated subagents. No time or usage ceiling is implied.

This boundary prevents coordinator context and sibling artifacts from biasing the experiment while preserving the capabilities of long-running agents.

## Identity and Namespace

The path order is always:

```text
<output-root>/<model-key>/<harness-key>/<experiment-key>/<run-id>/
```

`scripts/prepare_run.py` derives each identity key from:

1. a readable slug made from the normalized raw name
2. a SHA-256 prefix made from the exact raw UTF-8 name

The readable portion is not the identity. The digest distinguishes names that normalize to the same slug. A new UTC-and-random run ID prevents reruns from colliding, and atomic directory creation prevents overwrites.

Every model, harness, and experiment directory also contains a coordinator-owned `.oneshot-identity.json` marker:

```json
{"schemaVersion":"1.0","name":"<exact raw name>","key":"<derived directory key>"}
```

The coordinator writes each marker inside a private temporary namespace directory, then atomically publishes the complete directory. Concurrent preparers for the same exact identity verify the winning directory; an existing unmarked namespace is refused rather than adopted. This portable directory-rename protocol does not require hard-link support and turns even a digest-prefix collision into a classified reservation failure instead of shared storage. Published namespace markers are never rolled back—an empty, bound namespace is harmless, while deleting a shared parent marker during concurrent preparation is not. Workers receive write access only to their run directory, not to these markers. `templates/namespace-identity.json` documents the portable shape.

`run.json` preserves the raw names, derived keys, exact actual-prompt digest, run classification, and relative artifact path. `artifact/PROMPT.md` preserves the prepared prompt bytes passed to the lead—including any faithful custom-brief refinement—and travels with the deployable site.

Before dispatch, the coordinator also writes `.oneshot-provenance/<run-id>.json` under the output root. That receipt records the run path, identities, classification, prior-run relationship, prompt digest, and byte count outside the worker-owned run. After every initial run file and the receipt are closed, the coordinator atomically creates an empty `.oneshot-provenance/<run-id>.commit` marker. A run without that final marker was never ready for dispatch; the builder and validator can ignore its bounded initialization residue, including a partial receipt, so a killed preparation process does not poison later experiments. A committed run remains strict and visible even when its worker later damages or removes files.

Give the lead only its run path; do not include the receipt directory in its writable scope. The validator requires a one-to-one committed receipt and run inventory. This is a logical ownership boundary unless the harness enforces path-scoped writes; it is not tamper-proof against a worker with output-root access. When another harness reproduces the namespace without `prepare_run.py`, it must reproduce all three identity markers, the receipt, and the final empty commit marker.

## Dispatch Envelope

Create the lead with no inherited coordinator conversation. This must be an explicit harness setting, not an assumption about the word “fresh”: in Codex use `spawn_agent` with `fork_turns: "none"`; in another harness use its equivalent empty-history mode. A default that copies or forks the current conversation does not satisfy the isolation contract.

The initial lead dispatch contains only:

- `agents/oneshot-lead.md`
- the actual prompt as literal text
- raw and derived experiment identity
- the assigned run, workspace, and artifact paths
- any user-supplied inputs that belong to this experiment

Pass actual text even when it is also stored on disk. A path-only dispatch makes the benchmark dependent on an extra interpretation step. Do not include the aggregate manifest, sibling names, sibling prompts, sibling output paths, sibling artifacts, or sibling results.

When a catalogue baseline accompanies user context, include three unmodified blocks:

```text
BASELINE PROMPT (verbatim)
<catalogue prompt>

USER CONTEXT (verbatim)
<user context>

EXPERIENCE DIRECTION (verbatim)
<catalogue experienceDirection>
```

The labels identify provenance; they do not authorize the coordinator to rewrite any block. The third block ensures accepted baselines inherit the same visual, interaction-first posture as a catalogue selection without added context.

For an unmatched custom request, the actual prompt is a faithful refinement of no more than two paragraphs, not the rough input copied blindly. Preserve the user’s constraints and exact wording requirements, clarify the core experience, and add only loose experience-level guidance that follows from the request. Do not borrow from the catalogue when there is no genuine match. Store and dispatch that refined text exactly.

## Multiple Experiments

Plan all experiment identities and reserve all run paths before dispatch. Then create one fresh lead for each experiment.

- Dispatch all leads concurrently when the harness has enough isolated capacity.
- When capacity is lower than the experiment count, use batches without merging experiments or reusing lead contexts.
- A model-by-harness matrix produces one experiment run for every requested cell.
- Every lead may create its own internal team. Descendants inherit only their lead’s experiment scope and write only inside that experiment’s run.

The plan is valid when the number of distinct lead owners equals the number of experiment runs and all namespace paths are disjoint.

## Harness Capability Boundary

The workflow requires a real fresh-subagent primitive with an empty inherited conversation. Recursive delegation, persistent tasks, browser access, image generation, package installation, and other capabilities are optional enhancements that the lead may use when available.

If no-history subagents are unavailable, report `UNSUPPORTED_NO_FRESH_SUBAGENT` and stop before artifact generation. Same-context role-play, history-forked workers, coordinator generation, and prompt-only sequential imitation do not satisfy the contract.

Never add a goal-mode requirement, timeout, token cap, step limit, tool-call limit, or subagent limit to compensate for a harness difference. Record exposed runtime observations after completion without turning them into budgets.

## Completion and Reruns

The lead owns all implementation iteration inside its run. The coordinator may resume that same lead after an infrastructure pause, but does not inject sibling comparisons or post-process the artifact.

The lead may shape `workspace/` however it likes. Before completion it exports a static deployment into `artifact/` with the unchanged exact-case `PROMPT.md` and one exact-case root `index.html` entrypoint. That entrypoint does not imply a one-file artifact: all built runtime scripts, styles, media, fonts, models, data, and asset directories that serve the experience belong in the artifact tree. Local resources may use relative or root-relative URLs, their casing matches stored filenames, and `artifact/` is the deployment origin root. Deployment must not require an install, build, or application server step. Package manifests, source-only components, build or provider configuration, dependency and cache directories, server functions, secrets, and provider-filtered build state remain outside the entire artifact tree.

For the shared folder-drop target, the built artifact stays within 1,000 files, 5 MiB per file, and 100 MiB total. These final-upload bounds do not constrain workspace dependencies, source files, build assets, iteration, or delegation.

If the user requests another independent attempt:

1. preserve the original run unchanged
2. create a new run ID and fresh lead
3. store the new actual prompt or additional user instruction verbatim
4. set `classification` to `rerun` or `curated-attempt`
5. link the new run to the prior run in `run.json`

Transport recovery that resumes the same worker and workspace is not a rerun. Replacing the lead or starting a new artifact is.

## Worker Report

When the harness exposes the information, `worker-report.json` records:

- lead worker ID and descendant worker IDs
- status and blocker
- source build commands, the fixed artifact entrypoint, and static-deployment verification
- chosen technologies and external dependencies
- verification performed
- artifact file digests
- start and completion observations

Missing telemetry remains unknown. Never invent model version, cost, duration, token use, or agent count.

## See Also

- `references/catalog-index.md` — manifest, index, and validation contract
- `agents/oneshot-lead.md` — the lead’s portable role
