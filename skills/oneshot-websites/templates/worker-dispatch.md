# One-Shot Lead Dispatch

Coordinator requirement: create this lead with no inherited conversation history. In Codex, dispatch with `fork_turns: "none"`.

You own one isolated experiment. Follow `agents/oneshot-lead.md`.

- Model: {{MODEL_NAME}}
- Harness: {{HARNESS_NAME}}
- Experiment: {{EXPERIMENT_NAME}}
- Run directory: `{{RUN_PATH}}`
- Workspace: `{{RUN_PATH}}/workspace/`
- Static artifact: `{{RUN_PATH}}/artifact/`

## Prepared Actual Prompt (verbatim)

{{ACTUAL_PROMPT}}

Complete this prompt autonomously. You may create subagents and choose any implementation approach. Finish with the unchanged prepared prompt at `artifact/PROMPT.md` and a verified drop-ready website whose root entrypoint is `artifact/index.html`. This is not a one-file restriction: include whatever built asset tree makes the experience strongest.
