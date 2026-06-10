---
name: scaffold-github-copilot-hooks
description: "Scaffold GitHub Copilot hooks for repository-level Copilot cloud agent and Copilot CLI usage after auditing the project and verifying the live official GitHub docs. Use when a user asks for Copilot hooks, .github/hooks/*.json, Copilot CLI user hooks, preToolUse policy gates, permissionRequest automation, agentStop checks, hook refactors, or shared agent scripts. Generates a bash-first .github/hooks/copilot-hooks.json scaffold with adapter scripts under .github/copilot/hooks/generated and reusable project-script delegation. Do NOT use for generic Git hooks, Husky-only setup, Copilot cloud agent environment setup, Claude hooks, Codex hooks, or Devin hooks."
compatibility: "Requires: bash, jq, git, rg, python3"
metadata:
  version: "1.0.0"
  short-description: "Project-aware GitHub Copilot hook scaffolder"
  openclaw:
    category: "development"
    requires:
      bins: [bash, jq, git, rg, python3]
references:
  - project-analysis
  - hook-events
  - scaffold-layout
  - reusable-scripts
  - merge-strategy
  - gotchas
---

# scaffold-github-copilot-hooks

Audit the target project first, then scaffold GitHub Copilot hooks with a deterministic `.github/hooks/copilot-hooks.json` managed layer for Copilot cloud agent and Copilot CLI.

## Decision Tree

What is the user asking for?

- New repository-level Copilot hooks:
  Verify the live official GitHub hook docs, audit the project, choose a hook plan, then scaffold `.github/hooks/copilot-hooks.json`.
- Existing `.github/hooks/*.json`, `.github/copilot/settings*.json`, or hook scripts:
  Audit what already exists, choose `additive` or `overhaul`, then regenerate only the managed hook layer.
- Copilot CLI user-level hooks:
  Prefer repository hooks when behavior belongs to a repo; read `references/scaffold-layout.md` before writing user-level hooks under `~/.copilot/hooks/` or `$COPILOT_HOME/hooks/`.
- A hook must deny a tool call:
  Use `preToolUse` stdout JSON for both cloud agent and CLI. Use `permissionRequest` only for Copilot CLI permission-flow automation.
- A prompt asks for Copilot cloud agent environment setup:
  Use `{{ skill:scaffold-github-cloud-agent-environment }}` instead; this skill is for hooks, not runner setup workflows.
- Explanation only, not implementation:
  Read `references/hook-events.md` and `references/scaffold-layout.md`, then answer without editing files.

## Quick Reference

| Task | Action |
|------|--------|
| Verify the current official hook model | Run `scripts/verify_docs.py --json` and compare with `assets/hook-events.json` |
| Audit a target repo | Run `scripts/audit_project.sh /path/to/project` |
| Understand events, matchers, stdin payloads, and output decisions | Read `references/hook-events.md` |
| Design reusable repo-owned scripts | Read `references/reusable-scripts.md` |
| Decide additive vs overhaul | Read `references/merge-strategy.md` |
| Generate or refresh the managed hook scaffold | Run `scripts/scaffold_hooks.sh --project /path/to/project --plan /path/to/plan.json --mode additive|overhaul` |
| Merge generated hooks into `.github/hooks/copilot-hooks.json` | Let `scripts/scaffold_hooks.sh` call `scripts/merge_hooks_file.sh`, or run the merge script directly |
| Regenerate the hooks README in a target project | Run `scripts/render_hooks_readme.sh --project /path/to/project --plan /path/to/plan.json` |

## Non-Negotiable Workflow

1. Verify the live official GitHub Copilot hook docs before planning a real scaffold.
2. Compare the live event list, config file shape, matcher rules, command fields, output decision contracts, cloud-vs-CLI support, and exit-code semantics with `assets/hook-events.json`.
3. Audit the target project in detail before deciding which events to enable.
4. Inspect existing `.github/hooks/*.json`, `.github/copilot/settings.json`, `.github/copilot/settings.local.json`, `.github/copilot/`, `AGENTS.md`, and related automation before choosing a merge mode.
5. Inspect `.claude/settings*.json` only as inherited Copilot CLI context because the official docs say Copilot CLI can read cross-tool Claude settings. Do not write generated Copilot hooks there.
6. Produce or update a concrete hook plan JSON. Keep the scaffold deterministic by putting project-specific judgment into the plan, not into the scaffold script.
7. Prefer `.github/hooks/copilot-hooks.json` for generated repository hooks because `.github/hooks/*.json` is the documented repository-level location for both Copilot cloud agent and Copilot CLI.
8. Prefer repo-owned shared scripts for behavior that may move to Codex, Devin, OpenCode, Git hooks, GitHub Actions, or local shell usage. Keep generated Copilot hook files as thin adapters around those scripts.
9. Scaffold every current documented Copilot hook event as a commented bash stub under the managed hook root, even if the event stays disabled in `.github/hooks/copilot-hooks.json`.
10. Wire only the enabled events into `.github/hooks/copilot-hooks.json` so the project does not pay runtime cost for inactive stubs.
11. Do not copy Devin's exit-code-2 model. In Copilot, `preToolUse` denies through stdout JSON; `permissionRequest` treats exit code `2` as a CLI-only deny; other events mostly treat exit `2` as a warning or event-specific context.
12. Regenerate `.github/copilot/hooks/README.md` so the project always has a readable event map.
13. Tell the user to restart Copilot CLI after hook config changes because the official CLI docs say changes load when the CLI starts.

## Live Docs First

The official GitHub docs are the source of truth:

- `https://docs.github.com/en/copilot/concepts/agents/hooks`
- `https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/use-hooks`
- `https://docs.github.com/en/copilot/reference/hooks-reference`

If the official docs and this skill disagree, follow the official docs and update the local scaffold inputs before writing project files.

## Progressive Maintainer Drift Check

When updating this skill itself:

1. Live-fetch the three official GitHub Copilot hook docs pages on the day of the edit.
2. Compare the current event list, config locations, hook entry fields, matcher rules, payload aliases, output decisions, cloud-vs-CLI differences, `COPILOT_HOME`, and exit-code semantics with `assets/hook-events.json`.
3. If drift exists, update the whole scaffold surface together: `assets/hook-events.json`, `references/hook-events.md`, scaffold generators, templates, plan examples, validators, tests, evals, and thin wrappers.
4. If no drift exists, still mention that the live docs were checked. Do not update this skill from memory or by copying assumptions from Claude Code, Codex, Devin, or OpenCode.

## Project Analysis Rules

Before choosing any hook structure, inspect:

- repo root and workspace shape
- languages and package managers
- build, test, lint, and format entry points
- existing `.github/hooks/*.json` files and `.github/copilot/settings*.json`
- existing `.github/copilot/` scripts, instructions, cloud agent setup workflows, and Copilot docs
- existing `AGENTS.md`, skills, MCP configuration, and other agent instructions
- existing Claude config only as inherited Copilot CLI hook context; do not use it as the generated target
- existing Git hooks, Husky, Lefthook, or CI gates
- sensitive paths like `.env`, secrets, migrations, lockfiles, generated code, and infra directories
- reusable agent or automation scripts such as `<project>/scripts/agent-session-context.sh` and `<project>/scripts/agent-stop-checks.sh`

Run `scripts/audit_project.sh` first, then read `references/project-analysis.md` when you need the full checklist.

## Deterministic vs Project-Specific Work

Keep these parts deterministic:

- default hooks file path: `.github/hooks/copilot-hooks.json`
- default managed hook root path: `.github/copilot/hooks/generated`
- event stub filenames
- generated hook fragment shape with top-level `version: 1` and `hooks`
- merge behavior for previously managed hooks
- hooks README generation
- event manifest coverage for every current documented Copilot hook event

Allow these parts to stay project-specific:

- which events are enabled
- event matchers
- `timeoutSec`
- whether a configured script failure should deny or only log
- configured repo commands that an event should run before custom hook logic
- reusable repo-owned scripts that an event should delegate to before custom hook logic
- whether the refresh is `additive` or `overhaul`
- whether the user explicitly needs CLI user-level hooks in addition to repository hooks

## Scaffold Rules

- Generate bash scripts for the managed project hook runtime. Add PowerShell only when the project specifically needs Windows-native CLI hooks.
- Comment the generated bash stubs in plain language.
- Structure generated event scripts as `main()` plus a single `handle_event()` edit point so humans and agents can see the control flow quickly.
- Support language-agnostic `scripts` entries in the hook plan for reusable repo-owned scripts and `commands` entries for existing repo commands. Do not hard-code package managers, frameworks, or example toolchains into generated scripts.
- Put shared behavior in path-agnostic repo scripts, usually under `scripts/`, and pass a harness argument such as `copilot` when output protocols differ.
- Default to `.github/hooks/copilot-hooks.json` for repository config and `.github/copilot/hooks/generated` for generated adapter scripts.
- Keep one managed script per event so the event map stays obvious.
- Keep `.github/hooks/copilot-hooks.json` deterministic: remove only previously managed handlers, never unrelated custom hooks.
- Use `bash`, `powershell`, or `command` fields according to GitHub's config reference. Do not invent unsupported fields.
- Prefer camelCase event names for new generated config. Document PascalCase aliases only when VS Code-compatible payload fields matter.

## Reading Guide

| Need | Read |
|------|------|
| Full audit checklist and what to inspect first | `references/project-analysis.md` |
| Current official event list, matcher behavior, payload fields, decisions, and exit codes | `references/hook-events.md` |
| Managed folder layout and plan file shape | `references/scaffold-layout.md` |
| Reusable script placement across Copilot, Devin, Codex, OpenCode, Git hooks, and CI | `references/reusable-scripts.md` |
| Additive versus overhaul behavior | `references/merge-strategy.md` |
| `.github/hooks/*.json`, matcher, shell, cloud agent, and CLI pitfalls | `references/gotchas.md` |

## Operational Scripts

- `scripts/verify_docs.py` checks the live official GitHub docs for the expected hook contract.
- `scripts/audit_project.sh` builds a project profile from real repo signals.
- `scripts/scaffold_hooks.sh` renders the managed hook tree, manifest, README, and hooks fragment.
- `scripts/merge_hooks_file.sh` preserves non-managed hooks while replacing previously managed handlers.
- `scripts/render_hooks_readme.sh` rebuilds `.github/copilot/hooks/README.md` from the manifest and current plan.

## Gotchas

1. Repository-level hooks must live in `.github/hooks/*.json`. `.github/copilot/settings*.json` can contain inline hooks for Copilot CLI, but cloud agent loads `.github/hooks/*.json` by default.
2. Copilot hook files require top-level `version: 1` and `hooks`; this is different from Devin's `.devin/hooks.v1.json` shape.
3. `preToolUse` is fail-closed for command hooks. A crash, timeout, or non-zero exit can deny the tool call, so non-blocking `preToolUse` hooks must swallow internal failures after logging.
4. Exit code `2` is not a generic Copilot block signal. Use stdout JSON for `preToolUse`; use `permissionRequest` exit `2` only for CLI permission denials.
5. `permissionRequest` and `notification` are Copilot CLI-only surfaces. Cloud agent pre-approves tools and does not surface notifications.
6. Matchers are full-value regexes anchored as `^(?:pattern)$`; use `bash|edit`, not shell globs.
7. Cloud agent honors `bash` or `command`, runs in an ephemeral Linux sandbox, and has restricted outbound network. Do not depend on user-level hooks, local GUI notifications, or persisted log files there.
