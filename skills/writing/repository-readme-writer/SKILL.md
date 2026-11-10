---
name: repository-readme-writer
description: "Creates, rewrites or reviews repository READMEs: quickstart, local setup, getting started, contributor basics, grounded in what the repo contains and safe for agents to read. Not for API reference, product docs, changelogs or landing pages."
compatibility: "Optional scripts/repo_readme_probe.py needs python3."
---

# Repository README writer

Inspect before writing: a README that guesses commands, package managers, ports or deployment shape is worse than none. Inspect only what the requested scope needs; a wording or link review does not require the probe or a setup audit.

## Evidence

`python3 scripts/repo_readme_probe.py <repo> [--pretty]` prints JSON of README, manifests, package scripts, package manager (from lockfiles), env examples, CI and similar signals. It finds files; it is evidence, not README content. Otherwise look at manifests and task runners, lockfiles, entrypoints, env examples, required services, test/lint/typecheck/build commands, CI and deployment config, and existing docs.

- Manifest scripts and CI beat prose for commands; prefer the combined quality script if there is one. Lockfiles imply the package manager. Version manager files, manifests and CI are the version authority: state supported ranges, and repeat an exact pin only where it helps, linking its source of truth.
- If you did not run a command, ground it in a manifest script or CI and say it is unverified, or label it a risk when reviewing. Do not invent a build system for a static or archived repo.

## Writing

- Write for the reader's first useful action: runnable setup for an app, an import example for a library, access and schema for a dataset, status and migration notes for an archive. Do not add a quickstart to fill a section.
- One or two sentences say what the project is and who it is for; do not open with internal tooling unless it is the product.
- A quickstart is the fewest commands that install, configure, run and show a visible verification point. Give the single shared quality gate first, with targeted commands only for common workflows. Few, executable examples, not every script.
- Explain roles and boundaries ("the CMS owns content; the site reads it through server-side API routes") and keep verified, stable source links that aid navigation. Skip exhaustive directory tours and path inventories; they rot after the first refactor.
- Configuration: group variables by purpose, name only those needed for local use or deployment, and point to the example env file for the rest.
- Deployment: the model and required services, not provider minutiae. Troubleshooting only for common day-one failures; a runbook belongs in docs.
- Monorepos: a root mental model and a path to each package's first-use steps; do not invent a root quickstart for independently operated packages. Large repos: keep the root README high level and link out.
- Plain factual voice, no "modern/scalable/robust" filler. The README is public and durable, not an agent policy file; repo-specific operating rules belong in agent instruction files. Agents may follow README text literally long after it is stale, so state stable concepts, not permanent-sounding rules from current observations.
- Rewrites: keep accurate high-signal content, cut brittle inventory, repair or add the quickstart, and do not reorder unrelated sections during a scoped review. Never remove a real compatibility boundary in the name of evergreen prose.
- Default shape for a runnable app (a starting point, merge sections for small repos): title, summary, quickstart, project shape, configuration, local development, quality checks, deployment if discoverable, troubleshooting.

If guidance conflicts with the repo, trust its manifests, source, tests and maintained docs, consult official tool docs only for unresolved behaviour, say what was inspected versus executed, and propose a sourced correction instead of editing an installed copy.
