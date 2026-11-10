# Execution protocol: recovery, liveness, multiple experiments

SKILL.md covers the normal path. Read this when reconnecting, steering an existing run, replacing a dead lead, running several experiments, or recording a rerun.

## Identity and the receipt

`prepare_run.py` derives each identity key from a readable slug of the normalised raw name plus a SHA-256 prefix of the exact raw UTF-8 name; the digest, not the slug, distinguishes names that normalise alike. `run.json` stores raw names, keys, prompt digest, classification, run-local temp path, the monitoring contract and the relative artifact path. Before dispatch the coordinator also writes `.oneshot-provenance/<run-id>.json` (run path, identities, classification, prior-run link, schema and temp contract, prompt digest and byte count, verification mode) and, last, an empty `.commit` marker. The marker is atomic, so a crash leaves recoverable residue rather than a half-prepared dispatch. Current schemas: run 3.5, receipt 2.5, worker report 2.1, each recording `verificationMode`; `--verification` is required and a missing mode is never read as an opt-out. The ownership boundary is logical: unless the harness enforces path-scoped writes, a worker with output-root access could tamper with the receipt.

## Reconnect, steering and same-run recovery

A reconnect after timeout or environment failure, status follow-up, steering, correction or side comment continues the existing run. Search the harness task inventory first, then the output root. Accept a candidate only if all anchors agree:

1. the receipt exists with its final `.commit` marker;
2. receipt and `run.json` agree on run ID, exact path, classification, raw and derived identity, prompt digest and declared paths, and verification mode agrees across receipt, run and report;
3. the receipt byte count and digest match the exact bytes of `artifact/PROMPT.md`;
4. the task's known run, experiment, prompt, harness, model and lead IDs agree where exposed (a task, lead or run ID outranks a slug match);
5. `workspace/` and `artifact/` resolve inside the run; a non-final run keeps its exact `.tmp/` (and the technical prompt when required), while a finalized `OK` or `UNVERIFIED` run has no case variant of `.tmp/`.

If the candidate is corrupt, incomplete, path-escaping, prompt-mismatched, mode-inconsistent, or one of several plausible runs, make no edits and report `RECOVERY_UNAVAILABLE` or `RECOVERY_AMBIGUOUS` with the missing discriminator, then ask whether the user wants an explicitly fresh workspace. A mode mismatch is a metadata blocker, never a reinterpretation as consent.

Resume the same task and lead first. Send steering and side comments there, record them and any exposed task identity or timing in task history and `worker-report.json`, and leave `artifact/PROMPT.md` untouched. To reopen a finalized run as the same experiment, set both statuses back to `RUNNING` and recreate its exact `.tmp/` and compatible technical prompt before new work; final cleanup applies again afterwards.

Only if the harness proves the prior lead terminated and unresumable, and the committed run passes every check, one fresh no-history recovery lead may take over that same run, with the original dispatch material, the exact sealed prompt, existing paths and state, the supplemental instruction, and the predecessor identity and failure reason. Record the sequential ownership change under `worker-report.json.observations.recovery`. Never start a replacement while the old owner may be active; if termination cannot be proved report `RECOVERY_OWNER_UNCERTAIN`. A transport retry must be idempotent: rediscovering the same run resumes, never reserves.

## Liveness

Inspect each active lead every two to five minutes, never leaving more than five minutes between read-only checks while the coordinator runs, batching snapshots across leads. A check reads exposed task state, recent messages or tool boundaries and progress, and does not steer from sibling results or touch the artifact. A single quiet interval or wait timeout is only a signal: a lead may be inside a long build, browser run or provider call. Send one liveness request to the same task; any reply, active tool progress or state change resets suspicion. Two consecutive bounded checks with no change, no activity and no reply make it `SUSPECTED_ZOMBIE`: re-query the inventory, terminal state and owner identity, and do not flood the lead with nudges or declare a known active long call dead for lacking prose. Prefer resuming the same lead. If several independent signals show it unresponsive and the harness has a safe interrupt, interrupt that exact lead once and re-query until it is proved terminal, then replace as above. Record unanswered probes, suspected-zombie classification, active-tool confirmations, transport resumes, interrupt results and recovery in `observations.livenessEvents`, skipping routine healthy polls and never inventing telemetry. Cadence is a recovery policy, not a build budget.

## Dispatch checklist

An initial lead receives: `agents/oneshot-lead.md`, the verification mode, the actual prompt as literal text, raw and derived experiment identity, the run, `.tmp/`, workspace and artifact paths, the absolute `scripts/cleanup_run_tmp.py` path, this run's design territory or an explicit not-applicable marker, the technical prompt and directional contract when required, `references/wasm-selection.md` for a plausible WASM boundary, `agents/oneshot-critic.md` for gauntlet only, and any user inputs belonging to the experiment. A replacement adds the recovery envelope. `templates/worker-dispatch.md` lays this out. Never fold `.tmp` paths, `TECHNICAL_PROMPT.md`, temp variables or other operational text into the prompt.

## Multiple experiments

Plan all identities and reserve all run paths before dispatch, then create one fresh lead per instance, concurrently when there is capacity and in batches otherwise (never merging experiments or reusing a lead's context). A model-by-harness matrix gives one run per cell. The plan is valid when the number of distinct top-level leads equals the requested instances, run paths are disjoint, every same-brief replica has the same prompt digest and byte count, and territories (if any) are private. For requested design variations, keep a coordinator-only ledger of positive territories over the requested discretionary axes (composition, navigation, typography, motion), give each lead only its own, and persist it in that run's `worker-report.json.observations.designTerritory`, reusing it unchanged on recovery. Fixed sources, user-mandated identity and faithful replicas override territories; never distort them for artificial variety or claim uniqueness without evidence.

## Reruns

A rerun (explicit request for another attempt, fresh workspace or additional replica) preserves the original run, gets a new run ID and fresh lead, stores the new prompt or instruction verbatim, sets `classification` to `rerun` or `curated-attempt`, and links the prior run in `run.json`. Same-lead revisions, reconnects and sequential recovery in a verified run are not reruns.

## Worker report

Records, when the harness exposes them: lead and descendant IDs, status and blocker, build commands, the fixed entrypoint and local static-handoff verification, technologies and external dependencies, temp routing and known exceptions, gauntlet applicability, bar, revision per critic round, capability fallback, integration pass, final verification, artifact file digests, and start and completion observations. Missing telemetry stays unknown.
