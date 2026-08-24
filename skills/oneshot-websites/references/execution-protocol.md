# Autonomous One-Shot Execution Protocol

Use this reference when preparing runs, dispatching several experiments, adapting to harness capabilities, or recording a rerun.

## Meaning of One-Shot

One-shot means the coordinator gives one actual prompt to one fresh owning lead. The lead then has full agency to finish the experiment. It may use many model turns, tools, edits, tests, dependencies, and recursively delegated subagents. Every descendant may delegate again, with no skill-imposed per-parent count, total descendant count, or recursion-depth ceiling. No time or usage ceiling is implied.

This boundary prevents coordinator context and sibling artifacts from biasing the experiment while preserving the capabilities of long-running agents.

## Identity and Run Directory

Create each run directly below the caller-selected output root:

```text
<output-root>/<YYYY-MM-DD-HH-MM-SS>-<experiment-slug>/
```

The timestamp uses the coordinator’s local time, followed by a readable lowercase ASCII slug derived from the concise experiment name. `LibreOffice Writer`, for example, yields a run name such as `2026-07-31-20-05-46-libreoffice-writer`. `scripts/prepare_run.py` reserves the path atomically. When two preparations with the same slug land in the same second, the first keeps the base name and later reservations use `--02`, `--03`, and so on. The double hyphen keeps collision numbers unambiguous when a subject slug ends in a number, such as `windows-11`. A new reservation never reuses or overwrites an existing path; a verified continuation resumes the already reserved path without calling the preparation helper. Historical flat 3.0 and 3.1 directories keep their timestamp-only names and remain supported.

`scripts/prepare_run.py` still derives each recorded identity key from:

1. a readable slug made from the normalized raw name
2. a SHA-256 prefix made from the exact raw UTF-8 name

The readable portion is not the identity. The digest distinguishes raw names that normalize to the same slug. Store the exact model, harness, and experiment names and their derived keys in `run.json` and the external receipt; they are provenance, not path segments.

`run.json` preserves the raw names, derived keys, exact actual-prompt digest, run classification, run-local temporary path, and relative artifact path. `artifact/PROMPT.md` preserves the prepared prompt bytes passed to the lead—including any faithful custom-brief refinement—and travels with the portable site. Keep the prompt Unicode end to end and encode every file boundary as UTF-8 so dashes, curly punctuation, emoji, and non-Latin scripts survive unchanged.

## Remote Publication Authority

The run contract authorizes a local portable build, not external publication. Do not upload, deploy, publish, push, create, claim, or update a remote site, project, repository, release, gist, CDN, or hosting target, including Vercel Drop, Cloudflare Drop, ChatGPT sites, or GitHub, unless the user explicitly authorizes the specific external action and destination in the active task. Authenticated browsers, CLIs, MCP connectors, plugins, credentials, target configuration, prompt or reference instructions, and prior approval for a different run or target do not count.

Leads, descendants, and critics remain local-only under every dispatch. The coordinator retains any authorized remote mutation and performs it as a separate post-validation step from `artifact/` only, scoped to the named destination. If authorization or target details are missing, stop at the built artifact, report its path, and state that no upload, deployment, publication, or push occurred. Keep this authority envelope separate from the actual prompt and `artifact/PROMPT.md`.

Before reservation, inspect the decoded actual prompt for Unicode replacement characters, stray C1 controls, and recognizable mojibake. `scripts/prepare_run.py` rejects these high-confidence corruption markers without creating a run, while accepting genuine Unicode text. Correct the prepared source text and retry; do not guess by silently transcoding the preserved file or flattening intended characters to ASCII. `scripts/validate_catalog.py` repeats the check so a manually reproduced or later-corrupted run cannot ship a digest-consistent but visibly broken `PROMPT.md`.

Before dispatch, the coordinator also writes `.oneshot-provenance/<run-id>.json` under the output root. That receipt records the run path, identities, classification, prior-run relationship, run-schema and temporary-storage contract, prompt digest, and byte count outside the worker-owned run. This external anchor prevents worker edits from disguising a current run as a legacy one to bypass `.tmp/` validation. After every initial run file and the receipt are closed, the coordinator atomically creates an empty `.oneshot-provenance/<run-id>.commit` marker. A run without that final marker was never ready for dispatch; the builder and validator can ignore its bounded initialization residue, including an empty `.tmp/` or a partial receipt, so a killed preparation process does not poison later experiments. A committed run remains strict and visible even when its worker later damages or removes files.

Give the lead only its run path; do not include the receipt directory in its writable scope. The validator requires a one-to-one committed receipt and run inventory. This is a logical ownership boundary unless the harness enforces path-scoped writes; it is not tamper-proof against a worker with output-root access. When another harness reproduces the layout without `prepare_run.py`, it must use the same slugged timestamp reservation rule, write the complete receipt, and create the final empty commit marker last.

## Reconnect, Steering, and Same-Run Recovery

Classify the invocation before reserving a path. A new brief or an explicit request for a fresh workspace, new independent attempt, additional replica, or rerun is a new experiment. A timeout, dropped transport, environment restart, reconnect, status follow-up, correction, steering message, or side comment about an ongoing experiment is a continuation by default. Continuations reuse the existing harness task, lead namespace, run ID, run directory, `workspace/`, and `artifact/`; they do not call `scripts/prepare_run.py` merely because the coordinator reconnected. They retain the existing `.tmp/` for non-`OK` work, or recreate it only after an identity-verified completed run is explicitly reopened and moved back to `RUNNING`.

Search the harness task inventory first, then the caller-selected output root. Accept a recovery candidate only when all available identity anchors agree:

1. the coordinator-owned `.oneshot-provenance/<run-id>.json` receipt exists with its final empty `.commit` marker
2. receipt and `run.json` agree on the run ID, exact run path, classification, raw and derived identity, prompt digest, and declared paths
3. the receipt byte count and digest match the exact UTF-8 bytes of `artifact/PROMPT.md`
4. the task’s known run, experiment, prompt, harness, model, and lead identifiers agree wherever the harness exposes them
5. `workspace/` and `artifact/` resolve inside that one canonical run; a non-`OK` current run also retains its exact ordinary `.tmp/`, while a successfully finalized current run has no case variant of `.tmp/`

A known task, lead, or run ID outranks a name or slug match. A readable slug is never sufficient identity. If the candidate is corrupt, incomplete, path-escaping, prompt-mismatched, or one of several plausible runs, stop with `RECOVERY_UNAVAILABLE` or `RECOVERY_AMBIGUOUS`. Do not guess, combine runs, overwrite either candidate, or quietly create a fresh workspace; ask whether the user explicitly wants one.

Resume the same harness task and owning lead whenever possible. Send user steering, corrections, and side comments to that task rather than creating a sibling task or lead. Keep the sealed `artifact/PROMPT.md` unchanged: the initial actual prompt remains the provenance baseline, while later messages are supplemental continuation instructions. Preserve those messages in the existing harness history and, when the format permits, record their exact text plus exposed timing and task identity in `worker-report.json`; do not invent missing telemetry.

If the harness proves that the prior lead has terminated and cannot be resumed, but the committed run passes every identity check, a single fresh no-history recovery lead may continue in that same namespace. Before dispatch, confirm that no prior owner is active. Give the replacement the original lead and critic roles, exact sealed prompt, existing paths and state, current supplemental instruction, and exposed predecessor identity and interruption reason. It inspects the current workspace and artifact before changing anything and must not initialize, clear, copy, or fork the run. Set the current lead ID and record the predecessor, replacement, reason, and handoff under `worker-report.json.observations.recovery`. This is sequential ownership, not a second concurrent owner.

Only one lead may write an experiment namespace at a time. If the harness cannot prove the previous owner inactive, wait or report the recovery blocker. A transport retry must be idempotent: rediscovering the same committed run or task produces another resume attempt, not another run or replacement lead.

## Dispatch Envelope

Create every initial or replacement lead with no inherited coordinator conversation. This must be an explicit harness setting, not an assumption about the word “fresh”: in Codex use `spawn_agent` with `fork_turns: "none"`; in another harness use its equivalent empty-history mode. A default that copies or forks the current conversation does not satisfy the isolation contract. Resuming the same existing lead is not a new dispatch and retains that lead’s own task history.

The initial lead dispatch contains only:

- `agents/oneshot-lead.md`
- `agents/oneshot-critic.md`, included as operational role material for descendants rather than relying on ambient package discovery
- the actual prompt as literal text
- raw and derived experiment identity
- the assigned run, `.tmp/`, workspace, and artifact paths
- the absolute current `scripts/cleanup_run_tmp.py` path
- the operational temporary-file envelope from `templates/worker-dispatch.md`
- the recursive-team envelope from `templates/worker-dispatch.md`, including its inheritance, capability-preservation, scheduling, monitoring, and integration rules
- only this run’s private design territory from the coordinator’s design-diversity ledger for a multi-lead fan-out, or an explicit not-applicable marker for a single lead
- the complete `references/directional-controls.md` contract when the prepared receipt records `directionalControls.required: true`, or an explicit not-applicable marker otherwise
- the complete `references/wasm-selection.md` guidance when the request or supplied source presents a plausible compiled engine, codec, parser, database, emulator, simulation core, numerical hot path, or offline local-processing boundary
- any user-supplied inputs that belong to this experiment

A replacement recovery dispatch adds only the operational recovery envelope from `templates/worker-dispatch.md`: the continuation mode, same verified paths, current supplemental instruction, exposed predecessor identity, interruption reason, and instruction to inspect existing state before editing. It does not create or alter the actual prompt. Ordinary steering to a resumable lead is sent directly through the existing task and does not replay this initial dispatch.

Pass actual text even when it is also stored on disk. Populate that dispatch field by strictly decoding the sealed `artifact/PROMPT.md` bytes as UTF-8 after `prepare_run.py` succeeds; do not retype or rebuild it from a parallel string. When the harness exposes the serialized payload bytes, compare their SHA-256 digest with the prompt receipt before starting the lead. A path-only dispatch makes the benchmark dependent on an extra interpretation step. Keep any private design territory in a separate operational field. Do not include the aggregate manifest, sibling names or counts, sibling prompts, sibling design territories, sibling output paths, sibling artifacts, sibling captures, sibling critics, or sibling results.

The temporary-file envelope is lead-operational metadata, not part of the actual prompt. The coordinator creates `.tmp/` inside the unique run directory before dispatch. When the harness supports process-environment configuration, point `TMPDIR`, `TMP`, and `TEMP` at that absolute path for the lead; otherwise the lead applies those variables before launching local processes. The lead passes the same run-local path and supported overrides to descendants, retains `.tmp/` throughout active work, interruptions, recovery, and every non-`OK` outcome, keeps durable source in `workspace/`, and never copies `.tmp/` into `artifact/`. Tools may ignore overrides or create state before dispatch, so containment is explicitly best effort: record known exceptions instead of sweeping, moving, or deleting unrelated external paths.

Successful finalization is the only cleanup boundary. After the integrated artifact and local verification are complete, every outcome-relevant descendant and process has stopped, required evidence has moved into durable run files, and no final check depends on scratch state, keep `run.json` and `worker-report.json` at `RUNNING` and call the supplied absolute `scripts/cleanup_run_tmp.py` with the exact run path and `--confirm-finalized`. The helper verifies a supported receipt-anchored 3.2 or 3.3 identity, successful local evidence, an exact ordinary in-run target, and post-deletion absence before returning success. This lets an interrupted 3.2 run finish in place without spending a replacement workspace; already-completed 3.2 runs remain valid whether they retain their historical scratch or opt into cleanup, while every new 3.3 `OK` run must be clean. Only after the helper succeeds may a resumed run set both statuses to `OK` and run final catalog validation. Never replace this with a glob or broader recursive deletion. If the helper fails, the run remains non-`OK` with an explicit cleanup blocker. `PARTIAL`, `BLOCKED`, `ERROR`, interrupted, and otherwise recoverable runs retain `.tmp/` in its entirety. Reopening an identity-verified completed run as the same experiment first changes both statuses to `RUNNING` and recreates the exact ordinary `.tmp/`; it follows the same cleanup gate again before returning to `OK`.

The recursive-team envelope is also lead-operational metadata. Every descendant may create any number of further descendants, and the same permission continues through every generation without a skill-imposed per-parent, total-tree, or recursion-depth ceiling. Protect the lead and build-related descendants from arbitrary economy settings: do not disable, downgrade, or withhold model or harness capabilities available to their work, or add local budgets for their reasoning, context, turns, tools, delegation, or recursion. Critic descendants use the adaptive allocation policy in the quality gauntlet instead. Temporary concurrency and slot availability govern scheduling only: queue or batch useful pending branches and start them as capacity returns instead of truncating the plan. The lead remains accountable for the full tree, gives branches explicit tasks, deliverables, dependencies, write scopes, and evidence targets, monitors their states and results, resolves conflicts, accounts for outcome-relevant work, and performs a whole-artifact integration pass. Descendants inherit the same orchestration discipline for their subtrees. System, user, security, legal, and actual environment constraints remain authoritative, and unbounded delegation does not require pointless fan-out.

WebAssembly selection guidance is also operational metadata. Include it only for a plausible WASM boundary, and let the owning lead decide among a justified narrow module, a bounded representative spike, and the ordinary web stack. The lead role retains a compact decision gate for evidence discovered after dispatch. Never add generic WASM instructions to the actual prompt or mutate `artifact/PROMPT.md`; preserve an explicit user-authored WASM requirement normally when it is already part of the brief.

Never fold the `.tmp/` path, temporary environment variables, or this operational envelope into the actual prompt or `artifact/PROMPT.md`. Prompt provenance covers only the finished website brief.

When a catalogue baseline accompanies user context, preserve both sources while crafting one cohesive, fully developed actual prompt. Keep every explicit user constraint, use the catalogue goal only as the accepted baseline, and translate any useful visual or interaction posture into concrete details native to that experience. Do not impose a paragraph ceiling; six paragraphs is acceptable, and a brief may be longer when its substance requires it.

When the user fans out one brief without explicitly requesting variations—whether as multiple replicas, lead subagents, or workspaces—craft this actual prompt exactly once and seal one UTF-8 byte sequence. Prepare every instance from that same source, require matching SHA-256 digests and byte counts, and dispatch the same decoded prompt string without replica labels, variant guidance, or lead-specific amendments inside the prompt. Supply blind design diversity separately through the private operational territory below. The runs remain separate `autonomous-one-shot` attempts with no `priorRun`; simultaneous peers are not reruns.

`experienceDirection` is coordinator-only crafting guidance. Never include its literal value, a labelled `EXPERIENCE DIRECTION` block, or a generic paraphrase in the actual prompt, lead dispatch, or `PROMPT.md`. Provenance belongs in `run.json` and the coordinator receipt; the portable prompt should read as the finished brief, not as an assembly of internal instructions.

For an unmatched custom request, the actual prompt is a faithful, fully developed refinement, not the rough input copied blindly. Preserve the user’s constraints and exact wording requirements, clarify the core experience, and add only experience-level guidance that follows from the request. Do not borrow from the catalogue when there is no genuine match, and do not compress the prompt to an arbitrary paragraph or token target. Store and dispatch that refined text exactly. When the user requires their entire source brief to remain verbatim, preserve it byte-for-byte as the opening block and append only the subject-adapted mandatory prompt requirements: the completion mandate; when the brief depends on public `GET` data, its local-snapshot fallback; and for games, simulations, or 3D experiences with directional controls, its mouse-and-keyboard, directional-semantics, and production-state probe requirements. If they prohibit an applicable addition, report the incompatible constraint and stop before dispatch rather than weakening the prompt contract.

Every prepared actual prompt carries the catalogue’s `completionMandate` in subject-specific language. It explicitly rejects shortcuts and cookie-cutter approximations, states that the skill imposes no token budget limit, and asks for complete experiential depth. For replicas, clones, and emulators, this means fidelity across the original’s appearance, behavior, states, transitions, edge cases, and smallest meaningful interactions rather than a recognizable shell. For original work, it means comparable depth across primary and secondary interactions, motion, feedback, atmosphere, responsive states, and meaningful details. Do not paste the literal root value as boilerplate; express its requirements as part of the finished brief. The exact finished prompt—including this adapted mandate—is what the lead receives and what `artifact/PROMPT.md` preserves.

If the experience depends on unauthenticated public HTTP `GET` data, make resilience part of that finished actual prompt. Require the lead to bundle build-time local snapshots for the public responses needed by the meaningful default or primary experience even when live CORS works today, prefer schema-valid live data at runtime, and use the snapshots after a timeout, network or DNS failure, restrictive CORS policy, non-success response, malformed payload, or schema mismatch. A first-visit HTTP or browser cache is not a substitute for data already bundled in the artifact. The prompt must ask for honest source and capture-time disclosure where freshness matters, and live-success plus forced-fallback verification. Large and volatile feeds still qualify: a task-relevant bounded slice is acceptable when the complete feed is disproportionate, provided the interface does not overstate its coverage or freshness. Do not bundle secrets, authenticated or private responses, personal or sensitive data, or content without redistribution rights; use an explicit unavailable or empty state when a local copy would be inappropriate. Do not add this requirement to a brief with no public `GET` dependency.

Every game or simulation must have a practical mouse-and-keyboard path through its primary play loop; touch or controller input cannot be the only practical route. If a game, simulation, or 3D experience exposes directional movement, strafing, steering, turning, orbit, camera, or similar controls, make semantic direction correctness part of the finished actual prompt and provide paired WASD and arrow-key bindings by default: `A` with `ArrowLeft` for left, `D` with `ArrowRight` for right, `W` with `ArrowUp` for the mode-appropriate forward or upward action, and `S` with `ArrowDown` for the corresponding backward or downward action. Every visible, touch, pointer, or controller direction must agree in the active player-, camera-, character-, vehicle-, or mode-relative frame. Do not prescribe universal world-axis signs: require correctness through representative camera, character, or vehicle rotations, parent transforms, mirrored models or negative scales, and control-mode changes. Verification must observe rendered movement, heading, or orbit from the same seeded state rather than rely on key handlers or vector signs alone, and must confirm that ordinary mouse and complete keyboard input operate the primary experience. Preserve an explicit faithful nonstandard source mapping or user-selectable inversion option when requested, label it clearly, retain a practical mouse-and-keyboard path, and do not silently swap a presented control. For each applicable directional experience, the finished actual prompt also requires the production-state probe from `references/directional-controls.md`: it resets one seeded real state and exposes real position, forward, and active-frame right vectors so the coordinator can reject missing, zero, stale, or inverted `A`/left and `D`/right behavior with browser-level input. Keep the detailed schema in dispatch material, but make its subject-adapted delivery obligation explicit in the sealed prompt. Apply the directional requirement to a non-game 3D experience only when it actually exposes those controls.

## Multiple Experiments

Plan all experiment identities and reserve all run paths before dispatch. Then create one fresh lead for each experiment.

- Treat the user’s explicit “multiple lead subagents,” “multiple workspaces,” or “multiple replicas” language as an outer experiment count, never as inner delegation. Use the stated count, or two when “multiple” has no number.
- Each outer instance receives a sibling run directly under the output root, with its own `.tmp/`, `workspace/`, `artifact/`, receipt, commit marker, and fresh lead. Do not place several requested workspaces inside one run.
- Every repeated single-brief fan-out uses byte-identical prepared prompts and independent runs unless the user explicitly requests variations; peers do not receive invented variant labels or compare with one another.
- Every outer lead receives one private, mutually exclusive design territory for its discretionary choices and no information about any sibling territory, workspace, artifact, evidence, critic, or outcome.
- Dispatch all leads concurrently when the harness has enough isolated capacity.
- When capacity is lower than the experiment count, use batches without merging experiments or reusing lead contexts.
- A model-by-harness matrix produces one experiment run for every requested cell.
- Every lead may create an internal team of any useful breadth and depth. Each descendant may recursively create further descendants with no skill-imposed per-parent count, total-tree, or depth ceiling. Descendants inherit only their lead’s experiment scope, run-local temporary routing, paths, local-only authority, and recursive-team envelope, and write only inside that experiment’s run wherever the harness permits.

The plan is valid when the number of distinct top-level lead owners equals the number of requested experiment instances, all slugged timestamp run paths are disjoint, every same-brief replica has the same prompt digest and byte count, and each multi-lead run has a distinct private territory.

## Blind Design Diversity

Before dispatching any multi-lead fan-out, create a coordinator-only private design-diversity ledger. Keep the same sealed prompt for every repeated brief, but assign mutually exclusive positive design territories across composition and spatial organization, navigation and interaction structure, typography and colour language, and motion and feedback character. Give each lead only its own territory. Do not reveal the sibling count, names, territories, workspaces, artifacts, captures, reports, critics, outcomes, or comparative feedback, and do not let descendants inspect sibling paths even when a readable parent directory makes discovery technically possible. Never share one starter design system, template, component kit, reference shortlist, seed asset, screenshot, or critic observation across runs merely to coordinate differentiation.

The territory governs only discretionary design choices and stays outside the actual prompt and `artifact/PROMPT.md`. A fixed source, user-mandated identity, or faithful-replica constraint may require common traits; those traits are not lead design choices and should not be distorted for artificial variety. If the fixed source and prompt leave insufficient freedom for materially different designs, return `DIVERSITY_CONFLICT` before dispatch rather than weaken source fidelity, leak sibling decisions, or claim uniqueness that cannot be achieved. Persist the exact territory only in that run’s `worker-report.json.observations.designTerritory` and pass only it down that lead’s descendant and critic tree. A continuation or sequential recovery receives the same private territory unchanged.

## Harness Capability Boundary

The workflow requires a real fresh-subagent primitive with an empty inherited conversation. Recursive delegation, persistent tasks, browser access, image generation, package installation, and other capabilities are optional enhancements that the lead may use when available.

If no-history subagents are unavailable, report `UNSUPPORTED_NO_FRESH_SUBAGENT` and stop before artifact generation. Same-context role-play, history-forked workers, coordinator generation, and prompt-only sequential imitation do not satisfy the contract.

Never add a goal-mode requirement, timeout, token cap, step limit, tool-call limit, subagent-count limit, total-tree limit, recursion-depth limit, or capability downgrade to compensate for a harness difference. An actual concurrent-slot ceiling may require queues or batches, but it never becomes a smaller total topology. Record exposed runtime observations after completion without turning them into budgets.

## Lead-Owned Quality Gauntlet

Quality iteration stays inside the one fresh lead’s existing run. It does not create a new experiment, change the prepared prompt, or let the coordinator curate the artifact between rounds.

For non-trivial builds, the lead first turns the prompt and supplied references into a concrete, inspectable bar. When no direct reference exists, finding suitable category examples or defining subject-specific acceptance evidence is part of the work. The first fresh critic validates that bar and scores the artifact in one consolidated pass, rejecting a bar that is vague, unavailable, non-comparable, irrelevant, or materially weaker than the prompt. Freeze the accepted bar across rechecks; if evidence requires a legitimate revision, preserve the prior bar, revised bar, and reason. The lead owns decomposition: parallel work is appropriate only when concerns can be improved and judged independently. Coupled visual, interaction, state, and integration concerns stay with one sequential owner, and merged work receives a whole-artifact smoothing pass.

When recursive fresh descendants are supported, the lead creates a separate no-history critic from `agents/oneshot-critic.md`. The critic receives the actual prompt, proposed bar, relevant constraints, real built artifact, and the smallest sufficient inspectable captures, traces, or tests, but no builder explanation or history. It inspects the artifact directly under representative comparable conditions, validates the bar, and returns a verdict plus either `none` or the smallest coherent batch of material, co-fixable blockers. The critic never edits. `READY` is terminal for the inspected revision: non-blocking observations are recorded without a fix or another pass. After `NOT_READY`, the lead or its builder fixes the batch once and asks the same critic task for a targeted recheck of the affected states and proportionate regression evidence.

Mobile friendliness is part of the required gauntlet evidence. The lead and critic exercise at least one representative mobile viewport and inspect actual reflow, unintended horizontal overflow or clipping, legibility, navigation and control availability, touch targets, and the primary interaction path. Desktop captures, media-query presence, or resizing alone do not satisfy this check. A desktop-only exception requires a concrete prompt or faithful-source reason plus evidence that the narrow-viewport behavior is intentional rather than a silent mobile failure.

Mouse-and-keyboard usability is part of the required gauntlet evidence for every game or simulation: the lead and critic complete a representative primary path without relying on touch or a controller. Whenever a game, simulation, or 3D artifact exposes directional controls, they reset the same deterministic state, exercise each WASD and arrow-key pair independently, and inspect the rendered movement, heading, steering, or orbit relative to the active control frame. They repeat under a representative rotation, parent transform, mirrored model or negative scale, or alternate mode when one exists; compare pointer, touch, controller aliases, and visible labels; and treat key maps or vector-sign assertions as supporting evidence rather than proof. An explicit faithful nonstandard mapping or inversion option must be documented and retain a practical mouse-and-keyboard path, not be inferred to excuse an accidental swap.

Default to a quick, token-efficient critic and reserve expansive reasoning, context, turns, tool breadth, and token investment for build-related descendants. Keep the ordinary critic’s inputs and output focused, reuse prepared evidence and the prior critic task for targeted rechecks, and avoid implementation, broad exploratory research, open-ended redesign, repeated restatement, and routine critic fan-out. This is adaptive allocation, not a fixed numeric token, turn, or model cap. Escalate capability or add a new fresh or specialist critic only for a concrete review need such as a broad or coupled fix, a legitimate bar revision, a large coupled state space, subtle comparison, accessibility, security, or correctness risk, conflicting evidence, an inconclusive quick review, or an inspection format requiring greater capability; record the reason. If the quick configuration cannot inspect the actual artifact directly and compare it fairly, escalate or return `BLOCKED` rather than grading a summary or weakening the bar.

No lead- or skill-chosen fixed critic-round count is a completion condition, and the lean path is not a hard cap. The loop ends immediately on `READY`, when further differences are immaterial or trade away a stronger quality, when a genuine blocker prevents progress, or when the user stops the run. A `READY` verdict may reopen only when new material evidence invalidates it. An explicit user-requested stopping rule remains authoritative. If fresh recursive descendants are unavailable, the lead uses the strongest artifact-grounded browser, screenshot, interaction, test, or comparison evidence the harness supports to challenge both the bar and the artifact, and records the missing critic capability without claiming independent review.

Store full passes and targeted rechecks in the versioned structured `worker-report.json.qualityGauntlet` block, separate from final verification. The coordinator-owned receipt binds current run schema `3.3` to worker-report schema `2.1` and requires that block and completion-only temporary lifecycle, so a worker cannot delete the gauntlet record, downgrade cleanup, or masquerade as an older run. Every entry identifies the artifact revision, capture set, or digest actually inspected; the same critic worker ID may appear across targeted rechecks, and its coherent blocker batch fits the backwards-compatible `highestLeverageGap` field. Historical `NOT_READY` verdicts remain honest evidence even if the repaired artifact later reaches `READY`; they do not become failed items in the final-only `verification` array. The integration pass, gauntlet, static-handoff check, and final verification may reference one evidence bundle when it genuinely proves each claim for the same revision; no duplicate browser launch or capture set is required for reporting. Mark the gauntlet `required` for non-trivial builds. A genuinely trivial artifact may use `not-required` only with a concrete reason.

## Completion and Reruns

The lead owns all implementation iteration inside its run. After an infrastructure pause or reconnect, the coordinator first rediscovers and resumes that same task, lead, workspace, and run. User steering and side comments stay in that namespace; sibling comparisons remain excluded, and the coordinator does not post-process the artifact.

The lead may shape `workspace/` however it likes and keeps disposable run state in the sibling `.tmp/` until successful finalization removes that directory. Before completion it exports a portable static build into `artifact/` with the unchanged exact-case `PROMPT.md` and one exact-case root `index.html` entrypoint. That entrypoint does not imply a one-file artifact: all built runtime scripts, styles, media, fonts, models, data, and asset directories that serve the experience belong in the artifact tree. Local resources may use relative or root-relative URLs, their casing matches stored filenames, and `artifact/` is the origin root if a separately authorized deployment occurs. The artifact must not require an install, build, or application server step. Package manifests, source-only components, build or provider configuration, dependency and cache directories, run-local `.tmp/`, server functions, secrets, and provider-filtered build state remain outside the entire artifact tree.

For the shared folder-drop compatibility profile, the built artifact stays within 1,000 files, 5 MiB per file, and 100 MiB total. These portability bounds do not authorize an upload and do not constrain workspace dependencies, source files, build assets, iteration, or delegation. `artifact.staticDeploymentVerified` records local static-handoff verification only; it does not prove or require publication, and an entirely local run may reach `OK`.

After an applicable lead returns an `OK` artifact and removes `.tmp/`, the coordinator runs `scripts/verify_directional_controls.py --run <exact-run-directory>`. The helper sends `KeyA`, `ArrowLeft`, `KeyD`, and `ArrowRight` independently through Chromium’s DevTools input domain, computes semantic response from the adapter’s real vectors, hashes the artifact tree, and writes a coordinator-owned evidence receipt. `scripts/validate_catalog.py` rejects an applicable `OK` run when that evidence is missing, failed, incomplete, or bound to an older artifact revision. On failure, resume the same lead and namespace: return both statuses to `RUNNING`, recreate only that verified run’s `.tmp/`, supply the failing key evidence, and repeat normal finalization and verification. Do not spend a new run on this regression.

If the user explicitly requests another independent attempt, fresh workspace, additional replica, or rerun:

1. preserve the original run unchanged
2. create a new run ID and fresh lead
3. store the new actual prompt or additional user instruction verbatim
4. set `classification` to `rerun` or `curated-attempt`
5. link the new run to the prior run in `run.json`

Transport recovery that resumes the same worker and workspace is not a rerun. A sequential recovery lead in the same verified run is also not a rerun when the prior owner is proven terminated and the ownership change is recorded. Creating a new run, namespace, or independent artifact is a rerun and requires the user’s explicit fresh-attempt intent when an interrupted run already exists.

## Worker Report

When the harness exposes the information, `worker-report.json` records:

- lead worker ID and descendant worker IDs
- status and blocker
- source build commands, the fixed artifact entrypoint, and local static-handoff verification
- chosen technologies and external dependencies
- whether run-local temporary routing was applied and any known external exceptions
- quality-gauntlet applicability, concrete bar, artifact revision per critic round, capability fallback, integration pass, and final verification performed
- artifact file digests
- start and completion observations

Missing telemetry remains unknown. Never invent model version, cost, duration, token use, or agent count.

## See Also

- `references/catalog-index.md` — manifest, index, and validation contract
- `references/directional-controls.md` — applicable production-state adapter and browser gate
- `agents/oneshot-lead.md` — the lead’s portable role
