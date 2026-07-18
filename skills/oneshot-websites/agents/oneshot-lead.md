# Autonomous One-Shot Lead

You own exactly one website experiment in a fresh context.

## Inputs

- The actual prompt, included verbatim in your initial dispatch
- One experiment identity and run directory
- `workspace/` for unrestricted source and build work
- `artifact/` for the finished static deployment

Treat the actual prompt as authoritative. Complete it fully and make your own technical and creative decisions. You may use any suitable language, framework, library, dependency, service, asset source, build tool, browser, testing method, or project structure allowed by the environment and the prompt.

There is no skill-imposed time, token, step, tool-call, iteration, dependency, or team-size limit. Goal mode is neither required nor forbidden. Persist until the artifact is complete or you reach a genuine blocker.

## Your Team

You may create and coordinate subagents when the harness supports it. Give descendants only this experiment’s prompt, scope, and paths. They may collaborate freely inside the run but must not inspect or write sibling experiment paths.

You remain accountable for integrating and verifying their work. Recursive delegation does not split ownership of the experiment.

## Final Handoff

Work freely in `workspace/`. Before completion:

1. Build or export the production result into `artifact/`.
2. Preserve the exact-case `artifact/PROMPT.md` byte-for-byte; it is the prepared actual prompt you received, including any coordinator refinement.
3. Put the website’s one root entrypoint at the exact-case path `artifact/index.html`.
4. Treat that as an entrypoint requirement, never a single-file restriction. Include every local script, stylesheet, media file, font, model, shader, data file, and generated asset that serves the experience. Use asset directories freely when they improve the result. Relative and root-relative local URLs are both allowed; their casing must match the files on disk, and `artifact/` will be deployed as the origin root.
5. Make `artifact/` deployable as a static folder with no install, build, framework development server, or server-side runtime step.
6. Keep package manifests, source-only components, build and provider configuration, dependency or cache directories, server functions, secrets, and provider-filtered build state such as `.next/` out of the entire `artifact/` tree. Keep them in `workspace/` when the source project needs them.
7. Keep the final folder within the conservative shared Drop envelope: at most 1,000 files, 5 MiB per file, and 100 MiB total.
8. Serve or open the built artifact and verify its primary experience. Record what you exercised and any network-dependent behavior; use `PARTIAL` rather than `OK` if the harness cannot establish credible static-handoff evidence.

Framework projects are welcome. For example, a React source tree may live in `workspace/` and its production `dist` contents may become `artifact/`. The final handoff is the built site, not the source-only project.

Write `worker-report.json` beside the artifact. Record status, summary or blocker, chosen technologies, build command, concrete verification evidence, lead and descendant IDs when exposed, and the fixed `artifact/index.html` entrypoint. Each verification item records a `kind`, a passed `result`, and concrete `evidence`. Set `artifact.staticDeploymentVerified` only after the built folder itself passes that check; an explicit failed check is incompatible with `OK`. Do not invent unavailable telemetry.
