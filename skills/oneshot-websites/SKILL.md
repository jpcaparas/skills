---
name: oneshot-websites
description: "Run ambitious one-shot websites, web apps, games, simulations, clones, motion pieces, or benchmarks through fresh isolated subagents. Use for one-shot web artifacts, catalogue ideas, or parallel model/harness variants."
---

# Oneshot Websites

Give each experiment to a fresh lead subagent, pass it the actual prompt, and let it decide how to accomplish the task.

“One-shot” describes the delegation boundary: one initial task prompt and one owning lead subagent per experiment. It does not mean one model call, a short turn, a fixed stack, or a restricted workflow. The lead may work for as long as the task needs, use any suitable tools or dependencies, revise its own work, and create its own subagents. The build process is open; the final handoff is a static folder with one root `index.html`.

## Choose a Compatible Helper Runtime

The shipped coordinator helpers support Python 3.11 or newer; they do not require one exact minor release. In POSIX shells, set `ONESHOT_WEBSITES_PYTHON` to any compatible executable path or command name when `python3` is not the right interpreter. Every helper command below uses the same override:

```bash
"${ONESHOT_WEBSITES_PYTHON:-python3}" --version
```

The override names one executable and contains no flags. On Windows, select any compatible `python.exe`, or invoke a launcher such as `py -3` directly in place of the quoted expression. This runtime choice belongs only to the coordinator utilities; it places no language, framework, runtime, or dependency constraint on the one-shot lead.

## Route the Invocation

- **No brief or arguments:** immediately run `scripts/list_prompts.py` with no filters and present its complete catalogue before asking the user to choose. Do not silently shortlist the catalogue.
- **Exploratory context:** search the catalogue and offer only genuinely relevant matches as optional baselines. Keep a custom brief equally available. If there is no meaningful match, say so briefly and follow the user’s guidance without blending in catalogue material.
- **A clear or highly custom build brief:** use the brief itself as the actual prompt. When a catalogue item is materially relevant, offer it as an optional baseline, but dispatch the original brief unchanged unless the user accepts that match. If there is no real match, start the one-shot without forcing, mashing, or borrowing from a template; mere proximity is not relevance.
- **Several briefs, templates, models, or harnesses:** define one experiment per requested artifact. Never merge several one-shots into one worker.
- **Catalogue expansion:** read `references/catalogue-authoring.md`; append entries without changing existing IDs or imposing an implementation stack.
- **Artifact validation or indexing:** read `references/catalog-index.md`; validate provenance and the built root entrypoint without judging the chosen technology.

This routing step is complete when every requested artifact has one actual prompt and one experiment name, or the undecided user has the catalogue in front of them.

## 1. Preserve the Actual Prompt

For each experiment, identify the text the lead must act on:

- A direct brief stays byte-for-byte unchanged.
- A selected catalogue entry uses its `prompt` field unchanged.
- Combine a catalogue baseline with user context only when the user selected or accepted that baseline. Preserve and pass both verbatim as distinct labelled blocks; do not paraphrase either into a replacement brief.

Record the prompt before dispatch as the artifact’s `PROMPT.md`. Preserve its exact UTF-8 bytes and SHA-256 digest. Also write the pre-dispatch digest to the coordinator-owned provenance receipt outside the worker’s run. Pass the same actual text in the lead’s initial message, not merely a summary or file path.

Also record the raw model name, harness name, and experiment name. Use the active runtime’s reported names when available; use explicit `unknown-model` or `unknown-harness` labels rather than inventing specificity.

This step is complete when the stored bytes, digest, and text prepared for dispatch agree exactly.

## 2. Reserve a Collision-Free Namespace

Create the run before starting workers:

```text
<output-root>/
  .oneshot-catalogue.lock
  .oneshot-provenance/
    <run-id>.json
    <run-id>.commit
  <model-key>/
    .oneshot-identity.json
    <harness-key>/
      .oneshot-identity.json
      <experiment-key>/
        .oneshot-identity.json
        <run-id>/
          run.json
          worker-report.json
          workspace/
          artifact/
            PROMPT.md
            index.html
            ...
  index.html
```

Model comes first, harness second, experiment third. Each readable key also contains a strong digest prefix of its raw name, and each namespace level has a coordinator-owned `.oneshot-identity.json` marker binding that key to the exact raw name. A marker mismatch fails closed instead of co-mingling distinct identities. Every execution receives a new run ID. Existing runs are never reused or overwritten.

When Python is available, use:

```bash
"${ONESHOT_WEBSITES_PYTHON:-python3}" scripts/prepare_run.py \
  --output-root "<output-root>" \
  --model "<model-name>" \
  --harness "<harness-name>" \
  --experiment "<experiment-name>" \
  --prompt-file "<actual-prompt-file>"
```

On Windows, use a compatible `python.exe` or `py -3` launcher as described above. Choose a short output root and enable Win32 long-path support for deep source workspaces; the script and namespace rules are otherwise identical.

Read `references/execution-protocol.md` when planning multiple experiments, reproducing the namespace manually, recording a rerun, or adapting the contract to another harness.

The hidden receipt and its empty `.commit` marker are coordinator-owned. The marker is created last and atomically distinguishes a fully prepared dispatch from recoverable process-crash residue. Give the lead write authority only to its assigned run, never to the output root or receipt inventory. This is an ownership boundary, not a cryptographic one: if a harness cannot enforce path-scoped writes, the receipt is not tamper-proof against a worker with output-root access. `workspace/` is the lead’s unrestricted source and build area. `artifact/` is the final deployment root. This step is complete when every experiment has a distinct pre-created run directory, `artifact/PROMPT.md` matches the dispatched prompt and receipt, the commit marker exists, and no worker paths overlap.

## 3. Dispatch Fresh Lead Subagents

Actual generation belongs to subagents:

1. Create one fresh lead subagent for every experiment. The coordinator must not generate the artifact itself.
2. Create the lead with the harness's no-history isolation primitive so it inherits none of the coordinator conversation. In Codex, call `spawn_agent` with `fork_turns: "none"`; never rely on its history-inheriting default. Use the equivalent empty-context option in another harness.
3. Give the lead `agents/oneshot-lead.md`, its actual prompt verbatim, and only its assigned run path and experiment metadata in the initial dispatch. An empty inherited history does not replace the explicit role and prompt.
4. Keep coordinator history, sibling prompts, instructions, workspaces, artifacts, and outcomes out of its context.
5. Dispatch multiple requested experiments to multiple leads, concurrently whenever the harness has capacity. If capacity requires batches, retain one distinct fresh lead per experiment.
6. Let each lead create and coordinate its own subagents when the harness supports recursive delegation. Every descendant stays inside the lead’s experiment scope and namespace.

Fresh, no-history subagent support is a hard dependency. If the harness cannot create a subagent without inherited coordinator conversation, stop before generating the artifact, report `UNSUPPORTED_NO_FRESH_SUBAGENT`, and explain that this harness cannot satisfy the one-shot isolation contract. Do not substitute the coordinator or a sequential same-context imitation.

This step is complete when each experiment has exactly one distinct lead owner and every lead’s initial dispatch contains the exact assigned prompt.

## 4. Let the Leads Rip

On the lead’s work, the skill imposes no time, token, step, tool-call, dependency, source-file-count, framework, language, asset-source, browser-tool, testing-strategy, iteration, subagent-count, or subagent-depth budget. It does not require goal mode or any equivalent harness feature. The only fixed boundary is the deployable handoff described below.

Each lead may choose any architecture, libraries, services, generated assets, build system, collaboration pattern, verification workflow, and source-project shape that serve the actual prompt and the authority available in the environment. It may research, install dependencies, inspect screenshots, run the result, test interactions, and revise its implementation.

Before finishing, the lead builds or exports the result into `artifact/`. That folder must contain the unchanged, exactly cased `PROMPT.md` and one exactly cased root `index.html` entrypoint. It may also contain the built scripts, styles, media, and asset directories needed by the entrypoint. Local resource URLs may be relative or root-relative and must match stored filename casing; `artifact/` is deployed as the origin root. The folder must need no package installation, build command, framework development server, or server-side runtime after handoff. Package manifests, source-only component files, build or provider configuration, dependency and cache directories, server functions, secrets, and provider-filtered build state such as `.next/` stay out of the entire artifact tree. A React, Vue, Svelte, or other framework project is welcome in `workspace/`; copy its deployable production output, not its project tree, into `artifact/`.

The final folder, not the workspace, follows the conservative shared Drop envelope: at most 1,000 files, no file larger than 5 MiB, and no more than 100 MiB total. These are deployment-boundary constraints derived from the current static-host upload path, not limits on how the lead works or what it may use.

The coordinator waits for the owning lead and does not steer it with sibling results or rewrite its artifact afterward. If the harness pauses a long-running worker, resume the same lead when possible rather than replacing it. Normal system, user, security, legal, and environment rules still apply; this skill adds no implementation restrictions of its own.

This step is complete when each lead reports a finished drop-ready artifact or a genuine blocker, and all descendants and writes remain within the assigned experiment.

## 5. Record, Validate, and Present

Preserve each outcome, including partial or failed ones. Complete `run.json` and `worker-report.json` with:

- lead and descendant worker identifiers when exposed by the harness
- chosen tools, dependencies, and architecture
- build choices, verification, and the fixed `artifact/index.html` entrypoint
- status, blocker, and verification evidence
- timestamps, usage, duration, and cost only when the harness exposes them; these are observations, never limits

An internal revision by the same owning lead remains part of its autonomous one-shot. A separately dispatched rerun receives a new run ID and is labelled as a rerun or curated attempt; it never overwrites the original.

After all leads finish:

```bash
"${ONESHOT_WEBSITES_PYTHON:-python3}" scripts/build_catalog_index.py --root "<output-root>" --out "<output-root>/index.html"
"${ONESHOT_WEBSITES_PYTHON:-python3}" scripts/validate_catalog.py "<output-root>"
```

The index is a provenance and navigation surface. It links to each run’s `artifact/index.html` and `artifact/PROMPT.md` without assuming how the source project was built. Its artifact link identifies the entrypoint; it is not a substitute deployment origin for sites that use root-relative URLs. Concurrent index builders serialize the complete render-and-publish operation, so an older snapshot cannot overwrite a newer one. Validation requires the exact, current, readable root `index.html`, then cross-checks the coordinator receipt inventory, exact handoff paths and filename casing, conservative Drop envelope, local resources, excluded project state, and the lead’s recorded verification evidence. It is still a structural gate rather than a substitute for inspecting the deployed experience in a browser.

This step is complete when prompts and artifacts remain inspectable under the required namespace, successful artifacts can be deployed by dropping the `artifact/` folder onto a static host, statuses are honest, `artifact/index.html` resolves, and no run was overwritten.

## Reading Guide

| Need | Read |
| --- | --- |
| Show, search, or filter the current templates | Run `scripts/list_prompts.py`; the canonical data is `assets/prompt-catalogue.json` |
| Add future templates safely | `references/catalogue-authoring.md` |
| Dispatch workers, namespace runs, or handle reruns | `references/execution-protocol.md` |
| Build or validate the artifact index | `references/catalog-index.md` |
| Understand the research behind the breadth and provenance rules | `references/research-notes.md` |
| Give a lead its isolated role | `agents/oneshot-lead.md` |

## Package Validation

```bash
"${ONESHOT_WEBSITES_PYTHON:-python3}" skills/oneshot-websites/scripts/validate.py skills/oneshot-websites
"${ONESHOT_WEBSITES_PYTHON:-python3}" skills/oneshot-websites/scripts/test_skill.py skills/oneshot-websites
```
