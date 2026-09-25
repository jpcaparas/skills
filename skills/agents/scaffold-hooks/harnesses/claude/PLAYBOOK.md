# Claude Code Harness Playbook

Internal component of the `scaffold-hooks` skill. This playbook owns the Claude Code hook event contract, scaffolding scripts, and merge behavior. Paths are relative to `harnesses/claude/` unless noted.



Audit the target project first, then scaffold Claude Code hooks with a deterministic bash-first layout.

## Decision Tree

What is the user asking for?

- New Claude Code hooks in a project with no hook setup yet:
  Audit the project and installed-version evidence, resolve uncertain contracts from relevant official docs, choose a hook plan, then scaffold.
- Existing `.claude/settings*.json` or `.claude/hooks/` files:
  Audit what already exists, choose `additive` or `overhaul`, then regenerate only the managed hook layer.
- Existing hooks that show up in `/hooks` but never actually fire:
  Treat workspace trust as the first diagnostic. Check `~/.claude.json` for the exact project path before debugging settings or script logic, then offer to enable trust if it is still off.
- Existing hooks plus possible Claude Code feature drift:
  Verify the affected official contract before changing event semantics. If it exceeds the bundled helper, propose a canonical source update rather than silently editing installed inputs.
- Explanation only, not implementation:
  Use the reading guide to select only the reference needed for the question, then answer without scaffolding.

## Quick Reference

| Task | Action |
|------|--------|
| Verify the current official hook model | Read the live official docs at `https://code.claude.com/docs/en/hooks` and `https://code.claude.com/docs/en/hooks-guide`, then compare them to `assets/hook-events.json` |
| Audit a target repo | Run `scripts/audit_project.sh /path/to/project` |
| Check whether Claude Code trusts the target workspace | Run `scripts/check_workspace_trust.sh /path/to/project --json` |
| Enable workspace trust for the target workspace | Run `scripts/check_workspace_trust.sh /path/to/project --enable` |
| Understand the event catalog | Read `references/hook-events.md` |
| Design reusable repo-owned scripts | Read `references/reusable-scripts.md` |
| Decide additive vs overhaul | Read `references/merge-strategy.md` |
| Generate or refresh the managed hook scaffold | Run `scripts/scaffold_hooks.sh --project /path/to/project --plan /path/to/plan.json --mode additive|overhaul` |
| Merge managed hooks into settings | Let `scripts/scaffold_hooks.sh` call `scripts/merge_settings.sh`, or run the merge script directly |
| Regenerate the hooks README in a target project | Run `scripts/render_hooks_readme.sh --project /path/to/project --plan /path/to/plan.json` |

## Non-Negotiable Workflow

1. Use repository and installed-version evidence for stable local repairs; consult relevant live official docs when evidence is insufficient, stale, or event semantics will change.
2. Compare the affected event, hook type, or async contract with `assets/hook-events.json` before relying on it.
3. Audit the target project in detail before deciding which events to enable.
4. Inspect any existing `.claude/settings.json`, `.claude/settings.local.json`, `.claude/hooks/`, `CLAUDE.md`, `.claude/rules/`, and related automation files before choosing a merge mode.
5. Produce or update a concrete hook plan JSON. Keep the scaffold deterministic by putting project-specific judgment into the plan, not into the scaffold script.
6. Prefer a repo-owned shared `hooks/` tree for behavior that may move to Codex, OpenCode, Devin, Git hooks, GitHub Actions, or local shell usage. Keep Claude-specific files as thin adapters around shared event scripts.
7. The bundled generator renders every manifest event as `hooks/<event>/script.sh` plus `hooks/<event>/claude.{sh,json}`, even if the event stays disabled in settings; it has no selected-event-only layout mode.
8. Wire only the enabled events into the chosen settings file so the project does not pay runtime cost for inactive stubs.
9. Regenerate `hooks/README.md` so the project always has a readable event and adapter map.
10. If the user reports that hooks are registered but not firing, or you just completed a real scaffold and need to verify the setup, check or explicitly offer to check workspace trust for the exact project path before debugging hook logic.
11. If trust is disabled, explain that `hasTrustDialogAccepted` is false for that project. Offer the user two recovery paths: accept the dialog in a fresh Claude Code session, or flip the flag directly. Only mutate `~/.claude.json` when the user asks you to do so or explicitly asks you to ensure trust is enabled.

## Trust First Heuristic

Default to a trust check early when any of these signals appear:

- the user says hooks are not activating, not firing, or being ignored
- `/hooks` shows registered handlers with the expected counts, but nothing executes
- the hook scripts work when run by hand, but Claude Code never invokes them
- you just scaffolded hooks and the user wants you to confirm they actually work

Use this flow:

1. Canonicalize the target path first. Trust is keyed by the exact absolute project path.
2. Run `scripts/check_workspace_trust.sh /path/to/project --json`.
3. If status is `untrusted`, tell the user the flag is false and offer to enable it.
4. If the user wants it fixed, run `scripts/check_workspace_trust.sh /path/to/project --enable`.
5. Continue independent read-only checks of settings merges, matchers, permissions, and hook logic while trust is unresolved. Do not execute untrusted hooks or change trust without authorization.

## Contract Evidence

The official Claude Code docs are the source of truth:

- `https://code.claude.com/docs/en/hooks`
- `https://code.claude.com/docs/en/hooks-guide`

Use the two reading.sh articles only as secondary material for practical patterns and trade-off language:

- `https://reading.sh/claude-code-hooks-a-bookmarkable-guide-to-git-automation-11b4516adc5d`
- `https://reading.sh/claude-code-async-hooks-what-they-are-and-when-to-use-them-61b21cd71aad`

If official docs and secondary articles disagree, use evidence for the installed version and propose a canonical reference correction through the root `SKILL.md` maintenance route.

## Progressive Maintainer Drift Check

Live-fetch the official Claude Code docs relevant to an uncertain or changing contract, recording the source and applicable CLI version/date. Follow the root `SKILL.md` maintenance route: affected passage, proposed correction, and regression check. For authorized canonical changes, reconcile affected manifests, generators, templates, validators, tests, evals, and references. Do not update this skill from memory, mutate installed copies, or infer Claude capability from another harness. Wording-only and known local repairs need no full docs sweep.

## Project Analysis Rules

Before choosing any hook structure, inspect:

- repo root and workspace shape
- the exact absolute project path Claude Code will trust, because trust is keyed by path in `~/.claude.json`
- languages and package managers
- build, test, lint, and format entry points
- existing repo-owned command entry points such as task runners, package scripts, framework commands documented in the repo, CI jobs, Make/Just/Taskfile targets, and local scripts
- reusable agent or automation scripts such as `<project>/scripts/agent-session-context.sh`, `<project>/scripts/agent-stop-checks.sh`, adapter scripts, Husky hooks, and GitHub Actions jobs that should share logic
- monorepo tools like Turborepo, Nx, pnpm workspaces, Bun workspaces, or custom task runners
- existing Claude Code settings, rules, hooks, plugins, and skills
- existing Git hooks, Husky, Lefthook, or CI gates
- sensitive paths like `.env`, secrets, migrations, lockfiles, generated code, and infra directories
- environment reload needs such as `direnv`, `.envrc`, or per-directory tooling

Run `scripts/audit_project.sh` first, then read `references/project-analysis.md` when you need the full checklist.

## Deterministic vs Project-Specific Work

Keep these parts deterministic:

- shared hook root path
- event stub filenames
- managed settings fragment shape
- merge behavior for previously managed hooks
- hooks README generation
- event manifest coverage for every current official hook event

Allow these parts to stay project-specific:

- which events are enabled
- event matchers
- sync vs async choice
- `if` filters on tool events
- timeouts
- configured repo commands that an event should run before custom hook logic
- reusable repo-owned scripts that an event should delegate to before custom hook logic
- the actual logic inside enabled event scripts
- whether the refresh is `additive` or `overhaul`

## Repeat-Run Rules

When the skill is invoked again against a project:

- Consult relevant official docs when installed-version evidence is insufficient or the event contract changes.
- Re-audit the project before assuming the current hook plan still fits.
- If the user says hooks never fire, or the scaffold needs verification, re-check workspace trust for the exact project path before assuming the managed settings are wrong.
- Preserve non-managed hooks by default.
- Treat previously managed Claude adapters and `hooks/.state/claude` as replaceable in `overhaul` mode. Do not wipe the whole shared `hooks/` tree because other harnesses may own adapters there.
- Treat previously managed hooks as append-only in `additive` mode unless a missing event or stale README requires a refresh.
- If new official hook events are needed, propose a canonical manifest/generator/test update before claiming the helper supports them.

## Scaffold Rules

- Keep the bundled generator's Bash entrypoints and shared-script layout. Suitable repo-owned programs can run behind that protocol boundary through supported plan scripts/commands; Bash is not a universal Claude hook requirement.
- Comment the managed bash stubs in plain language.
- Structure managed event scripts as `main()` plus a single `handle_event()` edit point so humans and agents can see the control flow quickly.
- The helper runs `scripts[].path` through Bash. For non-Bash programs, use a Bash wrapper or `commands[].command` with an explicit interpreter; a shebang alone does not change the helper's invocation. Do not hard-code a project's toolchain into managed scripts.
- Put shared behavior in path-agnostic repo scripts, usually under `scripts/`, and pass a harness argument such as `claude` when output protocols differ. Managed event stubs should stay thin.
- Use `$CLAUDE_PROJECT_DIR` in managed command paths.
- Default to a shared hook root of `hooks`.
- Default to `.claude/settings.json` when the hook setup should be shared. Use `.claude/settings.local.json` only when the project needs machine-local behavior or already uses that pattern.
- Keep one shared `script.sh` per event and one Claude adapter/config pair per event so the event map stays obvious without duplicating event logic.
- Keep the merged settings deterministic: remove only previously managed handlers, never unrelated custom hooks.

## Reading Guide

| Need | Read |
|------|------|
| Full audit checklist and what to inspect first | `references/project-analysis.md` |
| Current official event list and support matrix | `references/hook-events.md` |
| Managed folder layout and plan file shape | `references/scaffold-layout.md` |
| Reusable script placement across Claude Code, Codex, OpenCode, Git hooks, and CI | `references/reusable-scripts.md` |
| Additive versus overhaul behavior | `references/merge-strategy.md` |
| Async, `if`, shell, and settings pitfalls | `references/gotchas.md` |

## Operational Scripts

- `scripts/audit_project.sh` builds a project profile from real repo signals.
- `scripts/check_workspace_trust.sh` checks or enables Claude Code workspace trust for an exact project path.
- `scripts/scaffold_hooks.sh` renders the managed hook tree, manifest, README, and settings fragment.
- `scripts/merge_settings.sh` preserves non-managed hooks while replacing previously managed handlers.
- `scripts/render_hooks_readme.sh` rebuilds `hooks/README.md` from the manifest and the current plan.

## Gotchas

1. `async` only applies to command hooks, and async hooks cannot block or steer Claude after the triggering action is already done.
2. The `if` field only works on tool events and requires Claude Code v2.1.85 or later.
3. `Stop` hooks can loop forever unless you honor `stop_hook_active`.
4. Hook shells are non-interactive. Shell profile noise can break JSON output.
5. `PermissionRequest` does not fire in non-interactive `-p` mode.
6. Hooks do not fire in untrusted workspaces. Claude Code gates execution on `hasTrustDialogAccepted` in `~/.claude.json` under `.projects["/absolute/path/to/project"]`. When hooks look installed but never run, or after a real scaffold, check trust first with `scripts/check_workspace_trust.sh` before blaming the hook config. See `references/gotchas.md` gotcha 9 for the exact recovery flow.
7. Do not bury reusable validation or context logic inside harness-specific adapters. Put shared logic in `hooks/<event>/script.sh` or repo-owned scripts, and let `hooks/<event>/claude.sh` handle only Claude Code protocol adaptation.
