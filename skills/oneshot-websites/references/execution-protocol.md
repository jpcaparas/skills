# Autonomous One-Shot Execution Protocol

Use this reference when preparing runs, dispatching several experiments, adapting to harness capabilities, or recording a rerun.

## Meaning of One-Shot

One-shot means the coordinator gives one actual prompt to one fresh owning lead. The lead then has full agency to finish the experiment. It may use many model turns, tools, edits, tests, dependencies, and recursively delegated subagents. No time or usage ceiling is implied.

This boundary prevents coordinator context and sibling artifacts from biasing the experiment while preserving the capabilities of long-running agents.

## Identity and Run Directory

Create each run directly below the caller-selected output root:

```text
<output-root>/<YYYY-MM-DD-HH-MM-SS>-<experiment-slug>/
```

The timestamp uses the coordinator’s local time, followed by a readable lowercase ASCII slug derived from the concise experiment name. `LibreOffice Writer`, for example, yields a run name such as `2026-07-31-20-05-46-libreoffice-writer`. `scripts/prepare_run.py` reserves the path atomically. When two preparations with the same slug land in the same second, the first keeps the base name and later reservations use `--02`, `--03`, and so on. The double hyphen keeps collision numbers unambiguous when a subject slug ends in a number, such as `windows-11`. No reservation reuses or overwrites an existing path. Historical flat 3.0 and 3.1 directories keep their timestamp-only names and remain supported.

`scripts/prepare_run.py` still derives each recorded identity key from:

1. a readable slug made from the normalized raw name
2. a SHA-256 prefix made from the exact raw UTF-8 name

The readable portion is not the identity. The digest distinguishes raw names that normalize to the same slug. Store the exact model, harness, and experiment names and their derived keys in `run.json` and the external receipt; they are provenance, not path segments.

`run.json` preserves the raw names, derived keys, exact actual-prompt digest, run classification, run-local temporary path, and relative artifact path. `artifact/PROMPT.md` preserves the prepared prompt bytes passed to the lead—including any faithful custom-brief refinement—and travels with the deployable site. Keep the prompt Unicode end to end and encode every file boundary as UTF-8 so dashes, curly punctuation, emoji, and non-Latin scripts survive unchanged.

Before reservation, inspect the decoded actual prompt for Unicode replacement characters, stray C1 controls, and recognizable mojibake. `scripts/prepare_run.py` rejects these high-confidence corruption markers without creating a run, while accepting genuine Unicode text. Correct the prepared source text and retry; do not guess by silently transcoding the preserved file or flattening intended characters to ASCII. `scripts/validate_catalog.py` repeats the check so a manually reproduced or later-corrupted run cannot ship a digest-consistent but visibly broken `PROMPT.md`.

Before dispatch, the coordinator also writes `.oneshot-provenance/<run-id>.json` under the output root. That receipt records the run path, identities, classification, prior-run relationship, run-schema and temporary-storage contract, prompt digest, and byte count outside the worker-owned run. This external anchor prevents worker edits from disguising a current run as a legacy one to bypass `.tmp/` validation. After every initial run file and the receipt are closed, the coordinator atomically creates an empty `.oneshot-provenance/<run-id>.commit` marker. A run without that final marker was never ready for dispatch; the builder and validator can ignore its bounded initialization residue, including an empty `.tmp/` or a partial receipt, so a killed preparation process does not poison later experiments. A committed run remains strict and visible even when its worker later damages or removes files.

Give the lead only its run path; do not include the receipt directory in its writable scope. The validator requires a one-to-one committed receipt and run inventory. This is a logical ownership boundary unless the harness enforces path-scoped writes; it is not tamper-proof against a worker with output-root access. When another harness reproduces the layout without `prepare_run.py`, it must use the same slugged timestamp reservation rule, write the complete receipt, and create the final empty commit marker last.

## Dispatch Envelope

Create the lead with no inherited coordinator conversation. This must be an explicit harness setting, not an assumption about the word “fresh”: in Codex use `spawn_agent` with `fork_turns: "none"`; in another harness use its equivalent empty-history mode. A default that copies or forks the current conversation does not satisfy the isolation contract.

The initial lead dispatch contains only:

- `agents/oneshot-lead.md`
- `agents/oneshot-critic.md`, included as operational role material for descendants rather than relying on ambient package discovery
- the actual prompt as literal text
- raw and derived experiment identity
- the assigned run, `.tmp/`, workspace, and artifact paths
- the operational temporary-file envelope from `templates/worker-dispatch.md`
- any user-supplied inputs that belong to this experiment

Pass actual text even when it is also stored on disk. Populate that dispatch field by strictly decoding the sealed `artifact/PROMPT.md` bytes as UTF-8 after `prepare_run.py` succeeds; do not retype or rebuild it from a parallel string. When the harness exposes the serialized payload bytes, compare their SHA-256 digest with the prompt receipt before starting the lead. A path-only dispatch makes the benchmark dependent on an extra interpretation step. Do not include the aggregate manifest, sibling names, sibling prompts, sibling output paths, sibling artifacts, or sibling results.

The temporary-file envelope is lead-operational metadata, not part of the actual prompt. The coordinator creates `.tmp/` inside the unique run directory before dispatch. When the harness supports process-environment configuration, point `TMPDIR`, `TMP`, and `TEMP` at that absolute path for the lead; otherwise the lead applies those variables before launching local processes. The lead passes the same run-local path and supported overrides to descendants, preserves `.tmp/` for inspection, keeps durable source in `workspace/`, and never copies `.tmp/` into `artifact/`. Tools may ignore overrides or create state before dispatch, so containment is explicitly best effort: record known exceptions instead of sweeping, moving, or deleting unrelated external paths.

Never fold the `.tmp/` path, temporary environment variables, or this operational envelope into the actual prompt or `artifact/PROMPT.md`. Prompt provenance covers only the finished website brief.

When a catalogue baseline accompanies user context, preserve both sources while crafting one cohesive, fully developed actual prompt. Keep every explicit user constraint, use the catalogue goal only as the accepted baseline, and translate any useful visual or interaction posture into concrete details native to that experience. Do not impose a paragraph ceiling; six paragraphs is acceptable, and a brief may be longer when its substance requires it.

When the user fans out one brief without explicitly requesting variations—whether as multiple replicas, lead subagents, or workspaces—craft this actual prompt exactly once and seal one UTF-8 byte sequence. Prepare every instance from that same source, require matching SHA-256 digests and byte counts, and dispatch the same decoded prompt string without replica labels, variant guidance, or lead-specific amendments. The runs remain separate `autonomous-one-shot` attempts with no `priorRun`; simultaneous peers are not reruns.

`experienceDirection` is coordinator-only crafting guidance. Never include its literal value, a labelled `EXPERIENCE DIRECTION` block, or a generic paraphrase in the actual prompt, lead dispatch, or `PROMPT.md`. Provenance belongs in `run.json` and the coordinator receipt; the deployable prompt should read as the finished brief, not as an assembly of internal instructions.

For an unmatched custom request, the actual prompt is a faithful, fully developed refinement, not the rough input copied blindly. Preserve the user’s constraints and exact wording requirements, clarify the core experience, and add only experience-level guidance that follows from the request. Do not borrow from the catalogue when there is no genuine match, and do not compress the prompt to an arbitrary paragraph or token target. Store and dispatch that refined text exactly. When the user requires their entire source brief to remain verbatim, preserve it byte-for-byte as the opening block and append only the subject-adapted completion mandate. If they prohibit even that required addition, report the incompatible constraint and stop before dispatch rather than weakening the prompt contract.

Every prepared actual prompt carries the catalogue’s `completionMandate` in subject-specific language. It explicitly rejects shortcuts and cookie-cutter approximations, states that the skill imposes no token budget limit, and asks for complete experiential depth. For replicas, clones, and emulators, this means fidelity across the original’s appearance, behavior, states, transitions, edge cases, and smallest meaningful interactions rather than a recognizable shell. For original work, it means comparable depth across primary and secondary interactions, motion, feedback, atmosphere, responsive states, and meaningful details. Do not paste the literal root value as boilerplate; express its requirements as part of the finished brief. The exact finished prompt—including this adapted mandate—is what the lead receives and what `artifact/PROMPT.md` preserves.

## Multiple Experiments

Plan all experiment identities and reserve all run paths before dispatch. Then create one fresh lead for each experiment.

- Treat the user’s explicit “multiple lead subagents,” “multiple workspaces,” or “multiple replicas” language as an outer experiment count, never as inner delegation. Use the stated count, or two when “multiple” has no number.
- Each outer instance receives a sibling run directly under the output root, with its own `.tmp/`, `workspace/`, `artifact/`, receipt, commit marker, and fresh lead. Do not place several requested workspaces inside one run.
- Every repeated single-brief fan-out uses byte-identical prepared prompts and independent runs unless the user explicitly requests variations; peers do not receive invented variant labels or compare with one another.
- Dispatch all leads concurrently when the harness has enough isolated capacity.
- When capacity is lower than the experiment count, use batches without merging experiments or reusing lead contexts.
- A model-by-harness matrix produces one experiment run for every requested cell.
- Every lead may create its own internal team. Descendants inherit only their lead’s experiment scope, run-local temporary routing, and paths, and write only inside that experiment’s run wherever the harness permits.

The plan is valid when the number of distinct top-level lead owners equals the number of requested experiment instances, all slugged timestamp run paths are disjoint, and every same-brief replica has the same prompt digest and byte count.

## Harness Capability Boundary

The workflow requires a real fresh-subagent primitive with an empty inherited conversation. Recursive delegation, persistent tasks, browser access, image generation, package installation, and other capabilities are optional enhancements that the lead may use when available.

If no-history subagents are unavailable, report `UNSUPPORTED_NO_FRESH_SUBAGENT` and stop before artifact generation. Same-context role-play, history-forked workers, coordinator generation, and prompt-only sequential imitation do not satisfy the contract.

Never add a goal-mode requirement, timeout, token cap, step limit, tool-call limit, or subagent limit to compensate for a harness difference. Record exposed runtime observations after completion without turning them into budgets.

## Lead-Owned Quality Gauntlet

Quality iteration stays inside the one fresh lead’s existing run. It does not create a new experiment, change the prepared prompt, or let the coordinator curate the artifact between rounds.

For non-trivial builds, the lead first turns the prompt and supplied references into a concrete, inspectable bar. When no direct reference exists, finding suitable category examples or defining subject-specific acceptance evidence is part of the work. Before artifact scoring, when available, a fresh critic rejects a bar that is vague, unavailable, non-comparable, irrelevant, or materially weaker than the prompt. Freeze the accepted bar across rounds; if evidence requires a legitimate revision, preserve the prior bar, revised bar, and reason. The lead owns decomposition: parallel work is appropriate only when concerns can be improved and judged independently. Coupled visual, interaction, state, and integration concerns stay with one sequential owner, and merged work receives a whole-artifact smoothing pass.

When recursive fresh descendants are supported, the lead creates a separate no-history critic from `agents/oneshot-critic.md`. The critic receives the actual prompt, bar, relevant constraints, real built artifact, and inspectable captures or tests, but no builder explanation or history. It inspects the artifact directly under representative comparable conditions, compares it with the bar, and returns a verdict plus one highest-leverage material gap. The critic never edits; the lead or its builder applies the change and gives the changed artifact to a new fresh critic.

No lead- or skill-chosen fixed critic-round count is a completion condition. The loop ends only when evidence shows the bar is met, further differences are immaterial or trade away a stronger quality, a genuine blocker prevents progress, or the user stops the run. An explicit user-requested stopping rule remains authoritative. If fresh recursive descendants are unavailable, the lead uses the strongest artifact-grounded browser, screenshot, interaction, test, or comparison evidence the harness supports to challenge both the bar and the artifact, and records the missing critic capability without claiming independent review.

Store critic history in the versioned structured `worker-report.json.qualityGauntlet` block, separate from final verification. The coordinator-owned receipt binds current run schema `3.2` to worker-report schema `2.1` and requires that block, so a worker cannot delete the gauntlet record and masquerade as an older run. Every round identifies the artifact revision, capture set, or digest actually inspected. Historical `NOT_READY` verdicts remain honest evidence even if the repaired artifact later reaches `READY`; they do not become failed items in the final-only `verification` array. Mark the gauntlet `required` for non-trivial builds. A genuinely trivial artifact may use `not-required` only with a concrete reason.

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
- quality-gauntlet applicability, concrete bar, artifact revision per critic round, capability fallback, integration pass, and final verification performed
- artifact file digests
- start and completion observations

Missing telemetry remains unknown. Never invent model version, cost, duration, token use, or agent count.

## See Also

- `references/catalog-index.md` — manifest, index, and validation contract
- `agents/oneshot-lead.md` — the lead’s portable role
