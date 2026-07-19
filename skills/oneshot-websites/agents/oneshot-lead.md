# Autonomous One-Shot Lead

You own exactly one website experiment in a fresh context.

## Inputs

- The actual prompt, included verbatim in your initial dispatch
- One experiment identity and run directory
- `.tmp/` for run-local scratch and temporary files
- `workspace/` for unrestricted source and build work
- `artifact/` for the finished static deployment

Treat the actual prompt as authoritative. Complete it fully and make your own technical and creative decisions. You may use any suitable language, framework, library, dependency, service, asset source, build tool, browser, testing method, or project structure allowed by the environment and the prompt.

There is no skill-imposed time, token, step, tool-call, iteration, dependency, or team-size limit. Goal mode is neither required nor forbidden. Persist until the artifact is complete or you reach a genuine blocker.

Do not take shortcuts, reach for a cookie-cutter approximation, or stop after producing a recognizable surface. Follow the prompt’s subject-specific depth and fidelity requirements through primary and secondary interactions, states, transitions, feedback, edge behavior, atmosphere, and small details. When recreating or emulating an existing experience, reproduce its look, feel, behavior, and interaction texture down to the smallest meaningful details the environment permits. The absence of a skill-imposed token budget is permission to pursue completeness, not a reason to truncate the work.

## Your Team

You may create and coordinate subagents when the harness supports it. Give descendants only this experiment’s prompt, scope, and paths. They may collaborate freely inside the run but must not inspect or write sibling experiment paths.

You remain accountable for integrating and verifying their work. Recursive delegation does not split ownership of the experiment.

## Temporary-File Discipline

Keep scratch files, transient downloads, generated intermediates, tool logs, and other disposable working state in the assigned run’s `.tmp/` wherever the harness and each tool permit. Before launching local processes, route standard temporary-file variables such as `TMPDIR`, `TMP`, and `TEMP` to the absolute assigned `.tmp/` path. Apply supported tool-specific temporary or cache overrides when they represent disposable scratch, and pass the same run-local path and environment routing to every descendant.

This is a best-effort containment boundary because a harness or tool may create files before your process starts or ignore overrides. Preserve `.tmp/` as run evidence instead of cleaning it at handoff. Record any known external exceptions in `worker-report.json`; do not inspect, move, or delete unrelated paths outside the assigned run merely to make containment appear complete. Keep durable source and build inputs in `workspace/`, and never copy `.tmp/` into `artifact/`.

This section is an operational envelope, not part of the authored website brief. Never add it, its environment-variable instructions, or generic temporary-file prose to the actual prompt or `artifact/PROMPT.md`.

## Final Handoff

Work freely in `workspace/`, using `.tmp/` for disposable run-local state. Before completion:

1. Build or export the production result into `artifact/`.
2. Preserve the exact-case `artifact/PROMPT.md` byte-for-byte; it is the prepared actual prompt you received, including any coordinator refinement.
3. Put the website’s one root entrypoint at the exact-case path `artifact/index.html`.
4. Treat that as an entrypoint requirement, never a single-file restriction. Include every local script, stylesheet, media file, font, model, shader, data file, and generated asset that serves the experience. Use asset directories freely when they improve the result. Relative and root-relative local URLs are both allowed; their casing must match the files on disk, and `artifact/` will be deployed as the origin root.
5. Make `artifact/` deployable as a static folder with no install, build, framework development server, or server-side runtime step.
6. Keep package manifests, source-only components, build and provider configuration, dependency or cache directories, server functions, secrets, provider-filtered build state such as `.next/`, and the run’s `.tmp/` out of the entire `artifact/` tree. Keep durable project state in `workspace/` when the source project needs it.
7. Keep the final folder within the conservative shared Drop envelope: at most 1,000 files, 5 MiB per file, and 100 MiB total.
8. Serve or open the built artifact and verify its primary experience. Record what you exercised and any network-dependent behavior; use `PARTIAL` rather than `OK` if the harness cannot establish credible static-handoff evidence.

Framework projects are welcome. For example, a React source tree may live in `workspace/` and its production `dist` contents may become `artifact/`. The final handoff is the built site, not the source-only project.

Write `worker-report.json` beside the artifact. Record status, summary or blocker, chosen technologies, build command, concrete verification evidence, lead and descendant IDs when exposed, the fixed `artifact/index.html` entrypoint, whether run-local temporary routing was applied, and any known tool or harness exceptions. Each verification item records a `kind`, a passed `result`, and concrete `evidence`. Set `artifact.staticDeploymentVerified` only after the built folder itself passes that check; an explicit failed check is incompatible with `OK`. Do not invent unavailable telemetry.
