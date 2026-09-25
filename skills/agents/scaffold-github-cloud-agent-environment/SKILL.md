---
name: scaffold-github-cloud-agent-environment
description: "Audit and scaffold `.github/workflows/copilot-setup-steps.yml` for GitHub Copilot cloud agent environments. Use for missing or broken setup workflows, runner/firewall/dependency/LFS/proxy issues, or Copilot setup repair. Do NOT use for generic GitHub Actions."
compatibility: "Requires: bash, jq, git, rg, and python3. Some fixes live in GitHub repository or organization settings and cannot be applied from the repository alone."
metadata:
  version: "1.0.0"
  short-description: "Project-aware GitHub Copilot cloud agent environment scaffolder and doctor"
  openclaw:
    category: "development"
    requires:
      bins: [bash, jq, git, rg, python3]
references:
  - live-docs
  - project-analysis
  - scaffold-layout
  - patterns
  - doctor-mode
  - gotchas
---

# scaffold-github-cloud-agent-environment

Make the target repository ready for Copilot cloud agent to build and validate changes. Start with repository and session evidence; consult relevant official GitHub documentation when a platform contract is uncertain, stale, or changing.

## Decision Tree

What is the user asking for?

- No `.github/workflows/copilot-setup-steps.yml` exists yet:
  Audit the repo, verify unresolved platform assumptions, draft a plan, resolve material blockers, then preview and scaffold the workflow.
- A `copilot-setup-steps.yml` file already exists but looks thin, stale, or incorrect:
  Inspect the workflow and failure evidence, then make the smallest justified repair while preserving custom steps. Use regeneration only for a deliberate replacement after previewing the diff and ensuring a recoverable backup.
- Agent runs fail or behave strangely after scaffolding:
  Run doctor mode first, use session-log evidence and repo facts to identify whether the fix is in-repo or in GitHub settings, then patch only what the evidence supports.
- The user only wants explanation or planning:
  Read only the references needed for the open question, then answer without scaffolding.

## Quick Reference

| Task | Action |
|------|--------|
| Resolve an uncertain platform contract | Select the relevant official URL from `references/live-docs.md` |
| Audit a target repository | Run `scripts/audit_project.sh /path/to/project` |
| Draft a plan from repo facts | Run `python3 scripts/suggest_plan.py --project /path/to/project` |
| Preview a generated workflow | Run `python3 scripts/render_setup_workflow.py --project /path/to/project --plan /path/to/plan.json --stdout` before a deliberate write |
| Diagnose an existing setup | Run `python3 scripts/doctor.py --project /path/to/project --symptom "describe the failure" --json` |
| Understand repo questions to ask before writing files | Read `references/project-analysis.md` |
| Choose ecosystem-specific dependency steps | Read `references/patterns.md` |
| Map symptoms to fixes | Read `references/doctor-mode.md` |

## Non-Negotiable Workflow

1. Use repository files, installed tool help/version evidence, and session logs for stable known repairs. Consult relevant live official docs when that evidence is insufficient, appears stale, or the platform contract will change; do not fetch every page for every repair.
2. Audit the repository before choosing steps, runners, or environment assumptions.
3. Distinguish repo-local fixes from GitHub settings fixes:
   - repo-local: `.github/workflows/copilot-setup-steps.yml`, `.github/copilot-instructions.md`, package-manager setup, LFS checkout, service containers
   - settings-level: runner policy, firewall allowlist, workflow approval, `copilot` environment secrets or variables
4. Keep project-specific judgment in the plan JSON, not buried inside the renderer.
5. Resolve material ambiguity from repository evidence first, then ask targeted questions for blockers. Record advisory choices as assumptions rather than blocking safe work. Potential blockers include:
   - the repo signals Windows, but the requirement is not explicit
   - multiple package managers or multiple toolchains compete
   - private registries or internal hosts are present
   - self-hosted or larger runners may be required
   - tests depend on services that are not obviously expressible as GitHub Actions `services`
6. Keep the workflow anchored to `.github/workflows/copilot-setup-steps.yml` with one job named `copilot-setup-steps`.
7. Only rely on documented job keys for that job. The bundled allowlist is `steps`, `permissions`, `runs-on`, `services`, `snapshot`, and `timeout-minutes`; verify relevant contract changes before extending it. The renderer does not implement every platform-supported key.
8. Treat setup-step failures as degraded environments, not hard stops. The docs say Copilot skips the remaining setup steps and continues with whatever environment exists at that point.
9. Default to deterministic dependency installation plus bounded code generation or preparation needed for a usable environment. Do not duplicate the full CI lifecycle by default. Expose build and validation commands through repo instructions.
10. In doctor mode, start with session logs and the observed symptom. Do not guess at fixes that the logs or repo facts do not support.

## Contract Evidence

Use the relevant official GitHub Docs page to resolve an open platform question; this is a source directory, not a mandatory reading list:

- `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/customize-the-agent-environment`
- `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/customize-the-agent-firewall`
- `https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-for-organization/configure-runner-for-coding-agent`
- `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/troubleshoot-cloud-agent`
- `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/track-copilot-sessions`
- `https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/configuring-agent-settings`
- `https://docs.github.com/en/copilot/tutorials/cloud-agent/get-the-best-results`
- `https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions`

Use `references/live-docs.md` for targeted refresh guidance and the proposed-update route. Versions, runner labels, key allowlists, and limits in bundled examples are snapshots, not perpetual upgrade requirements.

## Project Analysis Rules

Before you write or replace `copilot-setup-steps.yml`, inspect:

- whether `.github/workflows/copilot-setup-steps.yml` already exists
- package managers, lockfiles, and toolchain version files
- CI workflows and any existing runner choices
- `.github/copilot-instructions.md`, `.github/instructions/**/*.instructions.md`, `AGENTS.md`, `CLAUDE.md`, and `GEMINI.md`
- `.gitattributes` for Git LFS usage
- `.devcontainer/`, Dockerfiles, Compose files, and service requirements
- private-registry config files such as `.npmrc`, `.yarnrc.yml`, `pip.conf`, `.pypirc`, `.cargo/config.toml`, `nuget.config`, or `settings.xml`
- Windows-only or internal-network signals

Run `scripts/audit_project.sh` first, then read `references/project-analysis.md` when you need the full checklist and the question set.

## Deterministic Versus Heuristic Work

Keep these parts deterministic:

- the workflow path and job name
- explicit supported job keys for the verified platform contract
- a bounded timeout (`59` is the documented maximum in the bundled baseline; the renderer does not enforce it)
- validation triggers for easy manual and PR testing
- low-privilege `permissions`
- LFS enablement when the repo clearly uses Git LFS
- the doctor checks for missing workflow, wrong job name, unsupported job keys, missing checkout, and settings-only failure modes

Allow these parts to stay heuristic, but surface the assumptions:

- which runner strategy fits the repo
- whether the workflow should set up one toolchain or several
- exact dependency install commands
- whether service containers are safe to express in `services`
- whether the repo needs repo-level or org-level firewall or runner changes

If a heuristic choice can materially change correctness or safety, add it to `questions` and resolve it before applying the affected change. A labelled preview may retain unresolved blockers; it is not a deployable recommendation. Put non-blocking assumptions in `assumptions` or `notes`.

## Repeat-Run Rules

When the skill is invoked again against a project:

- Re-open relevant official docs when evidence is insufficient or stale, or a platform-sensitive contract will change.
- Re-audit the repo before assuming the existing plan still fits.
- Prefer a minimal patch that preserves custom steps, comments, and repository pins. The renderer replaces the whole workflow rather than merging it; use `--stdout` to review its output first and keep a recoverable backup before deliberate replacement. A plan's `mode` is not a no-clobber guard.
- Preserve the required job name and path on every refresh.
- Prefer improving a weak setup over adding second competing setup files.
- Use doctor mode first when the user reports failures from a real agent run.

## Scaffold Rules

- Write `.github/workflows/copilot-setup-steps.yml`, not a generic setup workflow under another name.
- Keep exactly one job named `copilot-setup-steps`.
- Only use supported job keys in that job.
- Keep `timeout-minutes` at `59` or lower.
- Add `workflow_dispatch`, `push`, and `pull_request` triggers scoped to the workflow file unless the user explicitly wants a quieter validation pattern.
- Add `contents: read` when the workflow checks out the repository.
- If the repo uses Git LFS, enable `lfs: true` on a compatible `actions/checkout` version consistent with repository pins. The bundled `@v5` example is a historical default, not a permanent platform requirement or an instruction to upgrade.
- Do not rely on a custom `fetch-depth` value. The live docs say Copilot overrides it.
- For self-hosted runners, require the user to disable the integrated firewall and allow the documented GitHub and Copilot hosts.
- For Windows runners, treat network controls as an explicit design decision because the integrated firewall is not compatible with Windows.
- Never inline credentials or secret values. Configure secrets and agent-wide variables through GitHub's documented environment/settings mechanism. Non-secret setup constants may use documented workflow `env` locations (the helper supports step-level `env`); the restricted setup-job allowlist does not imply job-level `env` support.
- Treat `.github/copilot-instructions.md` as a companion file whenever Copilot needs clear build, test, or validation commands.

## Doctor Mode

Doctor mode is for real failures after a scaffold or for repos with questionable existing setups.

Run `python3 scripts/doctor.py --project /path/to/project --symptom "what failed" --json`, then use the findings to decide the next action:

- local workflow fix: minimally patch `copilot-setup-steps.yml`; regenerate only for a reviewed replacement
- repo settings fix: update firewall or workflow-approval settings
- org settings fix: runner defaults or repository override policy
- session investigation: inspect the live session logs before changing files

Read `references/doctor-mode.md` for the symptom map and `references/gotchas.md` for the less obvious traps.

## Proposed Source Updates

When evidence exposes stale guidance, record the affected passage, current official source and applicable version/date, proposed change, and regression check. Edit the canonical source package only when maintenance is in scope; otherwise report the proposal, never silently mutate an installed copy. Reconcile documentation and helper behavior together for an authorized contract change, preserving least privileges, secret handling, and repository pins. See `references/scaffold-layout.md` for verified helper limits before relying on generated output.

## Reading Guide

| Need | Read |
|------|------|
| Official URLs and refresh policy | `references/live-docs.md` |
| What to inspect before choosing steps or runners | `references/project-analysis.md` |
| Generated file layout and plan JSON shape | `references/scaffold-layout.md` |
| Ecosystem setup patterns and when to ask questions | `references/patterns.md` |
| Session-log-led troubleshooting | `references/doctor-mode.md` |
| Default-branch, firewall, workflow-approval, and runner traps | `references/gotchas.md` |

## Operational Scripts

- `scripts/audit_project.sh` inspects a target repo and reports environment-relevant facts as JSON.
- `scripts/suggest_plan.py` turns repo facts into a draft plan with assumptions, manual settings, and questions.
- `scripts/render_setup_workflow.py` renders or refreshes `.github/workflows/copilot-setup-steps.yml` from an explicit plan.
- `scripts/doctor.py` diagnoses existing setup issues and separates repo changes from GitHub settings changes.
- `scripts/validate.py` checks structure, cross-references, and required support files.
- `scripts/test_skill.py` runs lightweight syntax and integration checks against temp repositories.

## Gotchas

1. The workflow only matters once it exists on the default branch. A correct file on a feature branch is still inert for real Copilot runs.
2. The live docs say only `steps`, `permissions`, `runs-on`, `services`, `snapshot`, and `timeout-minutes` are honored in the `copilot-setup-steps` job. Extra job keys may look valid but be ignored.
3. If a setup step exits non-zero, Copilot skips the remaining setup steps and continues anyway.
4. Self-hosted runners require the integrated firewall to be disabled in repository settings.
5. Windows runners are not compatible with the integrated firewall.
6. Organization-level runner policy can silently override a repository's preferred `runs-on`.
7. GitHub Actions workflows do not run automatically when Copilot pushes unless a human approves them or repository settings allow automatic runs.
8. `actions/checkout` `fetch-depth` is overridden by Copilot's platform behavior, so do not depend on a custom shallow-clone depth.
9. The firewall only applies to processes started by the agent in the Actions appliance. It does not protect setup steps or MCP servers.
10. If the repo depends on private registries or internal hosts, the real fix is usually a combination of `copilot` environment secrets or variables plus firewall or runner changes, not only a YAML edit.
