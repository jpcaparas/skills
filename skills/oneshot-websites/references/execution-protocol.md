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

`run.json` preserves the raw names, derived keys, exact actual-prompt digest, run classification, run-local temporary path, and relative artifact path. `artifact/PROMPT.md` preserves the prepared prompt bytes passed to the lead—including any faithful custom-brief refinement—and travels with the deployable site. Keep the prompt Unicode end to end and encode every file boundary as UTF-8 so dashes, curly punctuation, emoji, and non-Latin scripts survive unchanged.

Before reservation, inspect the decoded actual prompt for Unicode replacement characters, stray C1 controls, and recognizable mojibake. `scripts/prepare_run.py` rejects these high-confidence corruption markers without creating a run, while accepting genuine Unicode text. Correct the prepared source text and retry; do not guess by silently transcoding the preserved file or flattening intended characters to ASCII. `scripts/validate_catalog.py` repeats the check so a manually reproduced or later-corrupted run cannot ship a digest-consistent but visibly broken `PROMPT.md`.

Before dispatch, the coordinator also writes `.oneshot-provenance/<run-id>.json` under the output root. That receipt records the run path, identities, classification, prior-run relationship, run-schema and temporary-storage contract, prompt digest, and byte count outside the worker-owned run. This external anchor prevents worker edits from disguising a current run as a legacy one to bypass `.tmp/` validation. After every initial run file and the receipt are closed, the coordinator atomically creates an empty `.oneshot-provenance/<run-id>.commit` marker. A run without that final marker was never ready for dispatch; the builder and validator can ignore its bounded initialization residue, including an empty `.tmp/` or a partial receipt, so a killed preparation process does not poison later experiments. A committed run remains strict and visible even when its worker later damages or removes files.

Give the lead only its run path; do not include the receipt directory in its writable scope. The validator requires a one-to-one committed receipt and run inventory. This is a logical ownership boundary unless the harness enforces path-scoped writes; it is not tamper-proof against a worker with output-root access. When another harness reproduces the namespace without `prepare_run.py`, it must reproduce all three identity markers, the receipt, and the final empty commit marker.

## Dispatch Envelope

Create the lead with no inherited coordinator conversation. This must be an explicit harness setting, not an assumption about the word “fresh”: in Codex use `spawn_agent` with `fork_turns: "none"`; in another harness use its equivalent empty-history mode. A default that copies or forks the current conversation does not satisfy the isolation contract.

The initial lead dispatch contains only:

- `agents/oneshot-lead.md`
- the actual prompt as literal text
- raw and derived experiment identity
- the assigned run, `.tmp/`, workspace, and artifact paths
- the operational temporary-file envelope from `templates/worker-dispatch.md`
- any user-supplied inputs that belong to this experiment

Pass actual text even when it is also stored on disk. Populate that dispatch field by strictly decoding the sealed `artifact/PROMPT.md` bytes as UTF-8 after `prepare_run.py` succeeds; do not retype or rebuild it from a parallel string. When the harness exposes the serialized payload bytes, compare their SHA-256 digest with the prompt receipt before starting the lead. A path-only dispatch makes the benchmark dependent on an extra interpretation step. Do not include the aggregate manifest, sibling names, sibling prompts, sibling output paths, sibling artifacts, or sibling results.

The temporary-file envelope is lead-operational metadata, not part of the actual prompt. The coordinator creates `.tmp/` inside the unique run directory before dispatch. When the harness supports process-environment configuration, point `TMPDIR`, `TMP`, and `TEMP` at that absolute path for the lead; otherwise the lead applies those variables before launching local processes. The lead passes the same run-local path and supported overrides to descendants, preserves `.tmp/` for inspection, keeps durable source in `workspace/`, and never copies `.tmp/` into `artifact/`. Tools may ignore overrides or create state before dispatch, so containment is explicitly best effort: record known exceptions instead of sweeping, moving, or deleting unrelated external paths.

Never fold the `.tmp/` path, temporary environment variables, or this operational envelope into the actual prompt or `artifact/PROMPT.md`. Prompt provenance covers only the finished website brief.

When a catalogue baseline accompanies user context, preserve both sources while crafting one cohesive, fully developed actual prompt. Keep every explicit user constraint, use the catalogue goal only as the accepted baseline, and translate any useful visual or interaction posture into concrete details native to that experience. Do not impose a paragraph ceiling; six paragraphs is acceptable, and a brief may be longer when its substance requires it.

`experienceDirection` is coordinator-only crafting guidance. Never include its literal value, a labelled `EXPERIENCE DIRECTION` block, or a generic paraphrase in the actual prompt, lead dispatch, or `PROMPT.md`. Provenance belongs in `run.json` and the coordinator receipt; the deployable prompt should read as the finished brief, not as an assembly of internal instructions.

For an unmatched custom request, the actual prompt is a faithful, fully developed refinement, not the rough input copied blindly. Preserve the user’s constraints and exact wording requirements, clarify the core experience, and add only experience-level guidance that follows from the request. Do not borrow from the catalogue when there is no genuine match, and do not compress the prompt to an arbitrary paragraph or token target. Store and dispatch that refined text exactly. When the user requires their entire source brief to remain verbatim, preserve it byte-for-byte as the opening block and append only the subject-adapted completion mandate. If they prohibit even that required addition, report the incompatible constraint and stop before dispatch rather than weakening the prompt contract.

Every prepared actual prompt carries the catalogue’s `completionMandate` in subject-specific language. It explicitly rejects shortcuts and cookie-cutter approximations, states that the skill imposes no token budget limit, and asks for complete experiential depth. For replicas, clones, and emulators, this means fidelity across the original’s appearance, behavior, states, transitions, edge cases, and smallest meaningful interactions rather than a recognizable shell. For original work, it means comparable depth across primary and secondary interactions, motion, feedback, atmosphere, responsive states, and meaningful details. Do not paste the literal root value as boilerplate; express its requirements as part of the finished brief. The exact finished prompt—including this adapted mandate—is what the lead receives and what `artifact/PROMPT.md` preserves.

## Multiple Experiments

Plan all experiment identities and reserve all run paths before dispatch. Then create one fresh lead for each experiment.

- Dispatch all leads concurrently when the harness has enough isolated capacity.
- When capacity is lower than the experiment count, use batches without merging experiments or reusing lead contexts.
- A model-by-harness matrix produces one experiment run for every requested cell.
- Every lead may create its own internal team. Descendants inherit only their lead’s experiment scope, run-local temporary routing, and paths, and write only inside that experiment’s run wherever the harness permits.

The plan is valid when the number of distinct lead owners equals the number of experiment runs and all namespace paths are disjoint.

## Harness Capability Boundary

The workflow requires a real fresh-subagent primitive with an empty inherited conversation. Recursive delegation, persistent tasks, browser access, image generation, package installation, and other capabilities are optional enhancements that the lead may use when available.

If no-history subagents are unavailable, report `UNSUPPORTED_NO_FRESH_SUBAGENT` and stop before artifact generation. Same-context role-play, history-forked workers, coordinator generation, and prompt-only sequential imitation do not satisfy the contract.

Never add a goal-mode requirement, timeout, token cap, step limit, tool-call limit, or subagent limit to compensate for a harness difference. Record exposed runtime observations after completion without turning them into budgets.

## Completion and Reruns

The lead owns all implementation iteration inside its run. The coordinator may resume that same lead after an infrastructure pause, but does not inject sibling comparisons or post-process the artifact.

The lead may shape `workspace/` however it likes and keeps disposable run state in the sibling `.tmp/`. Before completion it exports a static deployment into `artifact/` with the unchanged exact-case `PROMPT.md` and one exact-case root `index.html` entrypoint. That entrypoint does not imply a one-file artifact: all built runtime scripts, styles, media, fonts, models, data, and asset directories that serve the experience belong in the artifact tree. Local resources may use relative or root-relative URLs, their casing matches stored filenames, and `artifact/` is the deployment origin root. Deployment must not require an install, build, or application server step. Package manifests, source-only components, build or provider configuration, dependency and cache directories, run-local `.tmp/`, server functions, secrets, and provider-filtered build state remain outside the entire artifact tree.

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
- whether run-local temporary routing was applied and any known external exceptions
- verification performed
- artifact file digests
- start and completion observations

Missing telemetry remains unknown. Never invent model version, cost, duration, token use, or agent count.

## See Also

- `references/catalog-index.md` — manifest, index, and validation contract
- `agents/oneshot-lead.md` — the lead’s portable role
