# One-Shot Lead Dispatch

Create this lead with no inherited conversation history (Codex: `spawn_agent` with `fork_turns: "none"`). You own one isolated experiment. Follow `agents/oneshot-lead.md`, included below.

- Model: {{MODEL_NAME}}
- Harness: {{HARNESS_NAME}}
- Experiment: {{EXPERIMENT_NAME}}
- Receipt-anchored verification mode: `{{VERIFICATION_MODE}}` (`gauntlet` or `none`)
- Run directory: `{{RUN_PATH}}`
- Run-local temporary storage: `{{RUN_PATH}}/.tmp/`
- Transient technical prompt, when applicable: `{{RUN_PATH}}/.tmp/TECHNICAL_PROMPT.md`
- Temporary cleanup helper: `{{TEMP_CLEANUP_HELPER}}`
- Workspace: `{{RUN_PATH}}/workspace/`
- Static artifact: `{{RUN_PATH}}/artifact/`

Everything outside "Prepared Actual Prompt" is operational and never goes into `artifact/PROMPT.md`.

## Operational envelope

The mode above matches the receipt, `run.json` and `worker-report.json`; keep it unchanged and pass it to every descendant. The lead role carries the rules for verification mode, local-only publication, sibling blindness, team scope, temp routing, cleanup and handoff.

## Recovery

{{RECOVERY_ENVELOPE}}

For an initial lead use `INITIAL: this is a newly reserved run.` For a replacement lead, only after the prior owner is proven terminated and the receipt, run metadata, prompt digest and byte count, identities and paths all match: give the same run ID and paths, the supplemental instruction, and the predecessor identity and interruption reason. The replacement inspects and continues `workspace/`, `artifact/`, `worker-report.json` and `.tmp/` before editing, and never clears, reinitialises, copies or forks the run.

## Private design territory

{{PRIVATE_DESIGN_TERRITORY}}

Your own positive design direction for discretionary choices when the user requested variations; otherwise `NOT_APPLICABLE: no design variation requested.`

## WebAssembly guidance

{{WASM_SELECTION_GUIDANCE}}

The full contents of `references/wasm-selection.md` when a plausible WASM boundary exists; otherwise `NOT_APPLICABLE`.

## Directional-control guidance

{{DIRECTIONAL_CONTROL_GUIDANCE}}

For `gauntlet` runs with `run.json.interaction.directionalControls.required: true`: the exact `.tmp/TECHNICAL_PROMPT.md` plus the complete `references/directional-controls.md`. Otherwise `NOT_APPLICABLE: generation only.` or `NOT_APPLICABLE: no prepared directional-control browser gate.`

## Critic role

{{ONESHOT_CRITIC_ROLE}}

The full contents of `agents/oneshot-critic.md` for `gauntlet`, so this empty-history lead can hand it to descendants; otherwise `NOT_APPLICABLE: no critics or verification.`

## Prepared Actual Prompt (verbatim)

{{ACTUAL_PROMPT}}

Complete this prompt autonomously in the selected mode and finish with the unchanged prompt at `artifact/PROMPT.md` and the site at `artifact/index.html`, plus whatever asset tree serves the experience. In `none` mode label the result UNVERIFIED and make no claim about behaviour or tested portability. "Drop-ready" names the local handoff shape and is not permission to upload, deploy, publish or push anything.
