# Devin CLI Harness Playbook

Internal component of the `scaffold-hooks` skill. This playbook owns the Devin CLI hook event contract, scaffolding scripts, and merge behavior. Paths are relative to `harnesses/devin/` unless noted.



Audit the target project first, then scaffold Devin CLI hooks with a deterministic `.devin/hooks.v1.json` managed layer.

## Decision Tree

What is the user asking for?

- New Devin CLI hooks in a project with no hook setup:
  Audit the project and installed-version evidence, resolve uncertain contracts from relevant official docs, choose a hook plan, then scaffold `.devin/hooks.v1.json`.
- Existing `.devin/hooks.v1.json`, `.devin/config*.json`, or `.devin/hooks/` files:
  Audit what already exists, choose `additive` or `overhaul`, then regenerate only the managed hook layer.
- A hook must deny or block agent behavior:
  Use command hooks that intentionally return exit code `2`; read `references/hook-events.md` before deciding where the block belongs.
- Existing Claude hook config is present:
  Treat it as an inherited-config risk to inspect, not as the target. Do not write managed Devin hooks to Claude config paths.
- Explanation only, not implementation:
  Use the reading guide to select only the reference needed for the question, then answer without editing files.

## Quick Reference

| Task | Action |
|------|--------|
| Verify the current official hook model | Run `scripts/verify_docs.py` and compare with `assets/hook-events.json` |
| Audit a target repo | Run `scripts/audit_project.sh /path/to/project` |
| Understand events, matchers, stdin, stdout, and exit code `2` | Read `references/hook-events.md` |
| Design reusable repo-owned scripts | Read `references/reusable-scripts.md` |
| Decide additive vs overhaul | Read `references/merge-strategy.md` |
| Generate or refresh the managed hook scaffold | Run `scripts/scaffold_hooks.sh --project /path/to/project --plan /path/to/plan.json --mode additive|overhaul` |
| Merge managed hooks into `.devin/hooks.v1.json` | Let `scripts/scaffold_hooks.sh` call `scripts/merge_hooks_file.sh`, or run the merge script directly |
| Regenerate the hooks README in a target project | Run `scripts/render_hooks_readme.sh --project /path/to/project --plan /path/to/plan.json` |

## Non-Negotiable Workflow

1. Use repository and installed-version evidence for stable repairs; consult relevant live official docs when evidence is insufficient, stale, or event semantics will change.
2. Compare the affected event, matcher, I/O, environment, or exit-code contract with `assets/hook-events.json`.
3. Audit the target project in detail before deciding which events to enable.
4. Inspect existing `.devin/hooks.v1.json`, `.devin/config.json`, `.devin/config.local.json`, `.devin/hooks/`, `AGENTS.md`, and related automation files before choosing a merge mode.
5. Produce or update a concrete hook plan JSON. Keep the scaffold deterministic by putting project-specific judgment into the plan, not into the scaffold script.
6. Prefer `.devin/hooks.v1.json` for managed project hooks because Devin documents it as the recommended standalone hooks file.
7. Avoid Claude config as a Devin target. Do not write managed Devin hooks to `.claude/settings.json`, `.claude/settings.local.json`, `~/.claude.json`, or any Claude-only path.
8. Prefer a repo-owned shared `hooks/` tree for behavior that may move to Codex, Claude Code, OpenCode, Git hooks, GitHub Actions, or local shell usage. Keep Devin-specific files as thin adapters around shared event scripts.
9. The bundled generator renders every manifest event as `hooks/<event>/script.sh` plus `hooks/<event>/devin.{sh,json}`, even if it stays disabled in `.devin/hooks.v1.json`; it has no selected-event-only layout mode.
10. Wire only the enabled events into `.devin/hooks.v1.json` so the project does not pay runtime cost for inactive stubs.
11. Use exit code `2` for intentional blocking. Other non-zero exits are logged by Devin but do not block according to the official docs.
12. Regenerate `hooks/README.md` so the project always has a readable event and adapter map.
13. Tell the user to verify loaded hooks with Devin's `/hooks` slash command after opening Devin CLI in the target project.

## Contract Evidence

The official Devin docs are the source of truth:

- `https://docs.devin.ai/cli/extensibility/hooks/overview`
- `https://docs.devin.ai/cli/extensibility/hooks/lifecycle-hooks`

If official docs and this skill disagree, distinguish documented behavior from version-specific field observations. Resolve the installed release's contract and propose a canonical source correction through the root `SKILL.md` maintenance route; never silently modify an installed skill.

## Progressive Maintainer Drift Check

Live-fetch both official Devin docs only when an open question spans the overview and lifecycle contracts; otherwise read the relevant page. Record the affected passage, source/version or date, proposed change, and regression check. Reconcile affected canonical files only when maintenance is in scope. Do not update this skill from memory or infer Devin support from another harness's fields. Stable repairs and wording edits need no full docs sweep.

## Project Analysis Rules

Before choosing any hook structure, inspect:

- repo root and workspace shape
- languages and package managers
- build, test, lint, and format entry points
- existing `.devin/hooks.v1.json`, `.devin/config.json`, `.devin/config.local.json`, `.devin/hooks/`, and Devin-related docs
- existing `AGENTS.md`, skills, MCP configuration, and other agent instructions
- existing Claude config only as inherited-hook context; do not use it as the managed target
- existing Git hooks, Husky, Lefthook, or CI gates
- sensitive paths like `.env`, secrets, migrations, lockfiles, generated code, and infra directories
- reusable agent or automation scripts such as `<project>/scripts/agent-session-context.sh` and `<project>/scripts/agent-stop-checks.sh`

Run `scripts/audit_project.sh` first, then read `references/project-analysis.md` when you need the full checklist.

## Deterministic vs Project-Specific Work

Keep these parts deterministic:

- target hooks file path: `.devin/hooks.v1.json`
- shared hook root path
- event stub filenames
- managed hook fragment shape
- merge behavior for previously managed hooks
- hooks README generation
- event manifest coverage for every current documented Devin lifecycle event

Allow these parts to stay project-specific:

- which events are enabled
- event matchers for tool events
- timeouts
- whether failures block with exit code `2`
- configured repo commands that an event should run before custom hook logic
- reusable repo-owned scripts that an event should delegate to before custom hook logic
- the actual logic inside enabled event scripts
- whether the refresh is `additive` or `overhaul`

## Scaffold Rules

- Keep the bundled generator's Bash entrypoints and shared-script layout. Suitable repo-owned programs can run behind that protocol boundary through supported plan scripts/commands; Bash is not a universal Devin hook requirement.
- Comment the managed bash stubs in plain language.
- Structure managed event scripts as `main()` plus a single `handle_event()` edit point so humans and agents can see the control flow quickly.
- The helper runs `scripts[].path` through Bash. For non-Bash programs, use a Bash wrapper or `commands[].command` with an explicit interpreter; a shebang alone does not change the helper's invocation. Do not hard-code a project's toolchain into managed scripts.
- Put shared behavior in path-agnostic repo scripts, usually under `scripts/`, and pass a harness argument such as `devin` when output protocols differ.
- Use `$DEVIN_PROJECT_DIR` in managed command paths because Devin documents it as the project root environment variable.
- Default to a shared hook root of `hooks`.
- Keep one shared `script.sh` per event and one Devin adapter/config pair per event so the event map stays obvious without duplicating event logic.
- Keep `.devin/hooks.v1.json` deterministic: remove only previously managed handlers, never unrelated custom hooks.
- Use only output shapes specifically documented or verified for the installed Devin release. The documented `hookSpecificOutput` context shape below is supported; its similarity to Claude does not establish support for other Claude fields, `async`, or `if`.

## Reading Guide

| Need | Read |
|------|------|
| Full audit checklist and what to inspect first | `references/project-analysis.md` |
| Current official event list, matcher behavior, stdin fields, and exit code `2` | `references/hook-events.md` |
| Managed folder layout and plan file shape | `references/scaffold-layout.md` |
| Reusable script placement across Devin, Codex, OpenCode, Git hooks, and CI | `references/reusable-scripts.md` |
| Additive versus overhaul behavior | `references/merge-strategy.md` |
| `.devin/hooks.v1.json`, matcher, shell, and stop-loop pitfalls | `references/gotchas.md` |

## Operational Scripts

- `scripts/verify_docs.py` checks the live official Devin docs for the expected hook contract.
- `scripts/audit_project.sh` builds a project profile from real repo signals.
- `scripts/scaffold_hooks.sh` renders the managed hook tree, manifest, README, and hooks fragment.
- `scripts/merge_hooks_file.sh` preserves non-managed hooks while replacing previously managed handlers.
- `scripts/render_hooks_readme.sh` rebuilds `hooks/README.md` from the manifest and current plan.

## Gotchas

1. `.devin/hooks.v1.json` is the whole hooks object; do not wrap managed hooks under a top-level `"hooks"` key there.
2. Exit code `2` is the blocking signal. Exit code `1` and other errors are logged but do not block according to Devin's docs.
3. Matchers are regexes over `tool_name`, not permission globs. Use `^mcp__github__.*`, not `mcp__github__*`.
4. Non-tool events have no `tool_name`; use an empty matcher or omit it.
5. `Stop` hooks that block can loop unless they check `stop_hook_active`.
6. Devin can read Claude hook config by default, but this scaffold intentionally writes only `.devin/hooks.v1.json`.
7. Hook shells are non-interactive. Keep profile noise out of stdout because stdout is reserved for optional JSON decisions.
8. Emit empty stdout or one Devin-supported JSON object. `SessionStart` context uses `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}`, documented by Devin. Plain-text rejection was field-verified on v2026.5.26-8; that is a historical baseline, not a required version. See `references/gotchas.md` 6a.
9. In the recorded Devin CLI baseline, hook execution is not shown in the TUI. Silence is not failure: verify via `/hooks`, CLI logs, or the session transcript rather than assuming later versions have identical UI behavior. See `references/gotchas.md` 6b.
