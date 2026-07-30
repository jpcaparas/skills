# One-Shot Lead Dispatch

Coordinator requirement: create this lead with no inherited conversation history. In Codex, dispatch with `fork_turns: "none"`.

You own one isolated experiment. Follow `agents/oneshot-lead.md`.

- Model: {{MODEL_NAME}}
- Harness: {{HARNESS_NAME}}
- Experiment: {{EXPERIMENT_NAME}}
- Run directory: `{{RUN_PATH}}`
- Run-local temporary storage: `{{RUN_PATH}}/.tmp/`
- Workspace: `{{RUN_PATH}}/workspace/`
- Static artifact: `{{RUN_PATH}}/artifact/`

## Operational Runtime Envelope (not part of the actual prompt)

Keep scratch and temporary files in the assigned `.tmp/` wherever the harness and tools permit. Route standard temporary-file variables such as `TMPDIR`, `TMP`, and `TEMP` there before launching local processes, and pass the same run-local path and routing to every descendant. Preserve `.tmp/` for run inspection. If a tool ignores the routing or creates state before this lead starts, record that limitation without deleting or sweeping unrelated external paths. Never copy `.tmp/` into `artifact/`, and never add this operational envelope to the prepared actual prompt or `artifact/PROMPT.md`.

## Fresh Critic Role (operational; not part of the actual prompt)

The coordinator must include the complete current contents of `agents/oneshot-critic.md` here so this empty-history lead can pass the role to fresh critic descendants without relying on ambient package discovery.

{{ONESHOT_CRITIC_ROLE}}

## Prepared Actual Prompt (verbatim)

{{ACTUAL_PROMPT}}

Complete this prompt autonomously. You may create subagents and choose any implementation approach. Finish with the unchanged prepared prompt at `artifact/PROMPT.md` and a verified drop-ready website whose root entrypoint is `artifact/index.html`. This is not a one-file restriction: include whatever built asset tree makes the experience strongest.
