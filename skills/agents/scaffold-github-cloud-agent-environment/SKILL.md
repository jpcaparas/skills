---
name: scaffold-github-cloud-agent-environment
description: "Creates, repairs and diagnoses `.github/workflows/copilot-setup-steps.yml` for GitHub Copilot cloud agent: dependency, runner, firewall, LFS, private registry or proxy failures, and runs that fail only in the cloud. Not for general GitHub Actions."
compatibility: "Needs bash, jq, git, rg and python3. Firewall, runner policy, approval and `copilot` environment secrets live in GitHub settings and need the user's access."
---

# Copilot cloud agent environment

The goal is a repository where Copilot cloud agent can install dependencies and build. Start from repository evidence and, for failures, the session logs. The facts below were checked against GitHub's docs on 2026-11-10; open the relevant page before relying on any of them for a change that depends on it, and report any mismatch instead of silently updating this skill. Pages (all under `https://docs.github.com/en/copilot/how-tos/`): `use-copilot-agents/cloud-agent/customize-the-agent-environment`, `.../customize-the-agent-firewall`, `.../troubleshoot-cloud-agent`, `.../track-copilot-sessions`, `.../configuring-agent-settings`, and `administer-copilot/manage-for-organization/configure-runner-for-coding-agent`. Job syntax: `https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions`.

## Platform contract

- As of 2026-11-10 GitHub's docs say sessions can run in a cloud sandbox, on GitHub Actions, or in a custom environment, and that the setup-steps file, runner and Windows options apply only to sessions on GitHub Actions. Confirm which kind the user's sessions use before editing the file.
- The file is `.github/workflows/copilot-setup-steps.yml` with exactly one job named `copilot-setup-steps`. It has no effect for real runs until it is on the default branch.
- Only `steps`, `permissions`, `runs-on`, `services`, `snapshot` and `timeout-minutes` are honoured in that job; other keys look valid and are ignored. `timeout-minutes` is capped at 59.
- A setup step that exits non-zero does not stop the run: Copilot skips the remaining setup steps and starts work in whatever environment exists.
- Copilot checks the code out itself only after setup finishes, so install steps that read the repo need their own `actions/checkout`. It overrides `fetch-depth`, so never depend on a depth. Use `lfs: true` on checkout when `.gitattributes` has `filter=lfs`.
- The integrated firewall is incompatible with self-hosted and Windows runners (the user must disable it and allowlist GitHub and Copilot hosts for self-hosted). It covers only processes the agent starts, not setup steps or MCP servers.
- Organisation owners can force a runner type, silently overriding the repo's `runs-on`.
- Workflows do not run automatically on Copilot's pushes until a human approves or settings allow it. A "CI did not run" report is usually this, not a broken environment.
- Never inline secrets. Registry auth and proxies go in `copilot` environment secrets or variables, and the host itself needs a firewall allowlist entry or runner access, so a private registry failure is rarely just a YAML edit.

## Choices

- Keep setup to dependency installation and the code generation needed for a usable environment. Do not duplicate CI; put build, test and lint commands in `.github/copilot-instructions.md` (offer it when missing).
- Defaults for the generated file: `contents: read`, a timeout well under 59, and `workflow_dispatch` plus `push` and `pull_request` triggers on the workflow file so it can be tested.
- Repair an existing workflow minimally, preserving custom steps, comments and action pins. The renderer rewrites the whole file, so preview with `--stdout` and back up before any deliberate replacement. Keep the repo's existing action versions and runner labels; the bundled `actions/checkout@v7` and `ubuntu-latest` are only examples (on 2026-11-10 the docs' own example still used `actions/checkout@v6`, while the [actions/checkout releases](https://github.com/actions/checkout/releases) had reached v7.0.1; v7 needs Actions Runner v2.327.1 or later).
- Ask the user, rather than guess, when: more than one lockfile or toolchain competes, Bun has no bootstrap convention, a needed runtime version is undeclared, Windows or self-hosted/larger runners may be required, private registries or internal hosts appear, or test services may not fit Actions `services`. Record advisory choices as `assumptions` in the plan and carry on.
- Say which fixes are repo-local and which need GitHub settings (firewall allowlist, runner policy, approval, `copilot` environment secrets). Do not disable the firewall or move to self-hosted runners to paper over a missing allowlist.

## Scripts

Run from this skill directory against the target repository:

- `scripts/audit_project.sh <project>` prints repo facts as JSON (package managers, version files, LFS, registries, containers, Windows markers, existing workflow and instructions).
- `python3 scripts/suggest_plan.py --project <project> [--output plan.json]` drafts a plan with `questions` and `assumptions`.
- `python3 scripts/render_setup_workflow.py --project <project> --plan plan.json [--stdout]` renders the workflow. It refuses a plan with non-empty `questions` unless `--allow-questions`, which bypasses the check and writes files; combine it with `--stdout` for a labelled draft.
- `python3 scripts/doctor.py --project <project> --symptom "<what failed>" --json` reports findings split into repo changes and settings changes.

Read `references/scaffold-layout.md` before using the renderer for anything beyond the default plan: it has the plan shape and the helper's limits (no merge, `.yml` assumed, timeout not range-checked, no `snapshot`, only some step fields). Read `references/patterns.md` for per-ecosystem install steps. Read `references/doctor-mode.md` when a real agent run failed.
