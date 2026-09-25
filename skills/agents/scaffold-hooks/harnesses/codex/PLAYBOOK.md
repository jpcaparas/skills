# Codex Harness Playbook

Internal component of the `scaffold-hooks` skill. This playbook owns the Codex hook event contract, scaffolding scripts, and merge behavior. Paths are relative to `harnesses/codex/` unless noted.



Audit the target project first, then scaffold Codex hooks with the bundled deterministic layout. Event details below describe the recorded `0.133.0` baseline, not a required CLI version or a complete catalog of later releases.

## Decision Tree

What is the user asking for?

- New project-local Codex hooks in a repo with no hook setup yet:
  Audit the repo, inspect the installed version and effective feature/trust state, resolve uncertain contracts from relevant official sources, then scaffold within the authorized scope.
- Existing `.codex/hooks.json`, `.codex/config.toml`, or `.codex/hooks/` files:
  Audit what exists first, choose `additive` or `overhaul`, then refresh only the managed hook layer.
- Hooks that exist on disk but never seem to affect Codex:
  Inspect the effective `hooks` feature and project/hook trust early. Explain any activation blocker; continue independent read-only checks of `hooks.json` and scripts without first enabling or trusting them.
- Explanation only, not implementation:
  Use the reading guide to select only the reference needed for the question, then answer without scaffolding.

## Quick Reference

| Task | Action |
|------|--------|
| Verify the current official Codex hook model | Read `https://developers.openai.com/codex/hooks`, `https://developers.openai.com/codex/config-basic`, the generated schemas listed in `assets/hook-events.json`, and the runtime source links in that manifest |
| Audit a target repo | Run `scripts/audit_project.sh /path/to/project` |
| Inspect the effective `hooks` feature | Run `python3 scripts/check_hooks_feature.py --project /path/to/project --json` |
| Review/trust managed hook definitions | Open `/hooks` in Codex after scaffolding or changing `.codex/hooks.json` |
| Enable hooks in project config | Run `python3 scripts/check_hooks_feature.py --project /path/to/project --enable --scope project` |
| Enable hooks in user config | Run `python3 scripts/check_hooks_feature.py --project /path/to/project --enable --scope user` |
| Understand the current event catalog | Read `references/hook-events.md` |
| Design reusable repo-owned scripts | Read `references/reusable-scripts.md` |
| Decide additive vs overhaul | Read `references/merge-strategy.md` |
| Generate or refresh the managed hook scaffold | Run `scripts/scaffold_hooks.sh --project /path/to/project --plan /path/to/plan.json --mode additive|overhaul --ensure-feature project|user|off` |
| Merge managed handlers into `.codex/hooks.json` | Let `scripts/scaffold_hooks.sh` call `scripts/merge_hooks_json.sh`, or run the merge script directly |
| Regenerate the hooks README in a target project | Run `scripts/render_hooks_readme.sh --project /path/to/project --plan /path/to/plan.json` |

## Non-Negotiable Workflow

1. Start with repository and installed-version evidence. Consult relevant live official docs when the contract is uncertain, stale, or event semantics will change.
2. Compare the affected contract with `assets/hook-events.json`; use schemas/source matching the installed release, not unreleased `main` behavior.
3. Audit the target project in detail before deciding which events to enable or which commands to run.
4. Inspect the effective `hooks` feature in the target project before treating any repo-local `hooks.json` as active.
5. If the feature is off, establish why and obtain authorization before changing activation settings; do not override policy. For an authorized change:
   - default to project scope for shared repo scaffolds
   - use user scope for personal/global hooks or when the repo should not commit `.codex/config.toml`
6. Inspect any existing `.codex/config.toml`, `.codex/hooks.json`, `.codex/hooks/`, `AGENTS.md`, `README*`, and other automation files before choosing a merge mode.
7. Produce or update a concrete hook plan JSON. Keep the scaffold deterministic by putting project-specific judgment into the plan, not into the scaffold script.
8. Prefer a repo-owned shared `hooks/` tree for behavior that may move to Claude Code, OpenCode, Devin, Git hooks, GitHub Actions, or local shell usage. Keep Codex-specific files as thin adapters around shared event scripts.
9. The bundled generator renders every manifest event as `hooks/<event>/script.sh` plus `hooks/<event>/codex.{sh,json}`, even if that event stays disabled in `hooks.json`; it has no selected-event-only layout mode.
10. Wire only the enabled events into `.codex/hooks.json` so inactive stubs stay cheap.
11. Regenerate `hooks/README.md` so the target project always has a readable event and adapter map.
12. If hooks still appear inactive after a real scaffold, re-check the effective feature state, confirm the project layer is trusted, and review/trust the hook definitions in `/hooks`.

## Feature First Heuristic

Check `hooks` early whenever any of these signals appear:

- the user asks to scaffold Codex hooks into a repo
- `.codex/hooks.json` exists, but nothing seems to happen
- the user is unsure whether the feature flag is on
- a repo-local `.codex/config.toml` exists, but the effective feature still looks off
- existing config uses the legacy `codex_hooks` alias

Use this flow:

1. Canonicalize the target project path first.
2. Run `python3 scripts/check_hooks_feature.py --project /path/to/project --json`.
3. If the effective status is off, inspect config and policy. With authorization, enable canonical `[features].hooks = true` in the agreed scope:
   - `--scope project` for shared repo-local setups
   - `--scope user` for personal/global setups
4. Re-run the inspection after enabling.
5. After scaffolding or changing hook definitions, use `/hooks` to review them; trust changes require authorization before execution.
6. Read-only diagnosis of `hooks.json`, matchers, permissions, and script logic can proceed independently. Report activation as unverified until feature and trust gates are satisfied.

## Contract Evidence

The official Codex docs are the source of truth:

- `https://developers.openai.com/codex/hooks`
- `https://developers.openai.com/codex/config-basic`
- `https://developers.openai.com/codex/config-reference`

For an unresolved wire-format or parser question, select the relevant source below and use its release-matched revision:

- `https://github.com/openai/codex/tree/main/codex-rs/hooks/schema/generated`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/features/src/lib.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/features/src/legacy.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/lib.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/config/src/hook_config.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/engine/discovery.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/events/common.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/events/compact.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/hooks/src/events/permission_request.rs`
- `https://raw.githubusercontent.com/openai/codex/main/codex-rs/core/src/tools/hook_names.rs`

If docs and runtime source disagree, resolve the installed release's behavior with version-matched evidence and record the discrepancy. Do not assume a `main` branch schema is released. As of the bundled manifest, the canonical feature key is `hooks`; `codex_hooks` is a legacy alias.

Use the article at `https://reading.sh/codex-hooks-just-gave-you-back-complete-control-over-your-code-57d044bcae1b` as secondary material for practical patterns, not as the source of truth. Early hook writeups drifted as the feature evolved.

## Progressive Maintainer Drift Check

Live-fetch the official Codex hook docs relevant to uncertain or changing semantics; compare with the installed CLI version, generated schemas, and runtime source only as needed to resolve that question. Record the affected passage, source/version, proposed change, and regression check using the root `SKILL.md` maintenance route. For authorized canonical changes, reconcile affected manifests, generators, templates, validators, tests, evals, and references. Do not update this skill from memory or patch an installed copy silently. Stable local repairs and wording edits do not require fetching every schema.

Known drift: the official hooks page reviewed on 2026-09-25 documents `SessionEnd`, `Interrupt`, async command hooks, and MCP tool hooks beyond this bundled baseline. These are not implemented by this generator; extending them needs a separate version-matched manifest/generator/test update, not an automatic upgrade.

## Project Analysis Rules

Before choosing any hook structure, inspect:

- repo root and workspace shape
- whether the project already has `.codex/config.toml`, `.codex/hooks.json`, or `.codex/hooks/`
- languages and package managers
- build, test, lint, format, and validation entry points
- existing repo-owned command entry points such as task runners, package scripts, framework commands documented in the repo, CI jobs, Make/Just/Taskfile targets, and local scripts
- reusable agent or automation scripts such as `<project>/scripts/agent-session-context.sh`, `<project>/scripts/agent-stop-checks.sh`, adapter scripts, Husky hooks, and GitHub Actions jobs that should share logic
- monorepo tools like Turborepo, Nx, pnpm workspaces, Bun workspaces, Cargo workspaces, or custom task runners
- existing AI instructions such as `AGENTS.md`, project rules, or repo automation docs
- existing Git hooks, Husky, Lefthook, or CI gates
- sensitive paths like `.env`, secrets, lockfiles, generated code, migrations, and infra directories
- whether the hook setup should be shareable in repo config or kept user-local

Run `scripts/audit_project.sh` first, then read `references/project-analysis.md` when you need the full checklist.

## Deterministic vs Project-Specific Work

Keep these parts deterministic:

- shared hook root path
- event stub filenames
- managed `hooks/.state/codex/hooks.json` fragment shape
- merge behavior for previously managed hooks
- hooks README generation
- event manifest coverage for every current official Codex hook event
- feature-flag inspection and reporting

Allow these parts to stay project-specific:

- which events are enabled
- matcher regexes for supported events
- timeouts and status messages
- configured repo commands that an event should run before custom hook logic
- reusable repo-owned scripts that an event should delegate to before custom hook logic
- whether feature enablement belongs in project or user config
- the actual logic inside enabled event scripts
- whether the refresh is `additive` or `overhaul`

## Repeat-Run Rules

When the skill is invoked again against a project:

- Re-check relevant official docs/schemas when installed-version evidence is insufficient or event semantics change.
- Re-audit the project before assuming the current hook plan still fits.
- Re-check the effective feature state before assuming repo-local hooks are active.
- Preserve non-managed hooks by default.
- Treat previously managed Codex adapters and `hooks/.state/codex` as replaceable in `overhaul` mode. Do not wipe the whole shared `hooks/` tree because other harnesses may own adapters there.
- Treat previously managed hooks as append-only in `additive` mode unless the managed layer or README is stale.
- If the official event set or parser rules changed, propose the canonical source update before using unsupported scaffold inputs.

## Scaffold Rules

- Keep the bundled generator's Bash entrypoints and shared-script layout. Repo-owned programs in suitable languages can run behind that boundary through supported plan scripts/commands; Bash is not a universal Codex architecture requirement.
- Comment the managed bash stubs with the event-specific input and output contract.
- Structure managed event scripts as `main()` plus a single `handle_event()` edit point so humans and agents can see the control flow quickly.
- The helper runs `scripts[].path` through Bash. For non-Bash programs, use a Bash wrapper or `commands[].command` with an explicit interpreter; a shebang alone does not change the helper's invocation. Do not hard-code a project's toolchain into managed scripts.
- Put shared behavior in path-agnostic repo scripts, usually under `scripts/`, and pass a harness argument such as `codex` when output protocols differ. Managed event stubs should stay thin.
- Default to a shared hook root of `hooks`.
- Default to a hooks file target of `.codex/hooks.json`.
- The component helper defaults to enabling `hooks` in `.codex/config.toml`; use `--ensure-feature off` when activation changes are not authorized.
- Use `~/.codex/config.toml` only when the hook setup should stay personal or machine-local.
- Keep one shared `script.sh` per official event and one Codex adapter/config pair per event so the event map stays obvious without duplicating event logic.
- Keep the merged `hooks.json` deterministic: remove only previously managed handlers, never unrelated custom hooks.
- The bundled baseline skips `async`, `prompt`, and `agent` hooks; do not infer newer support from this generator. Verify the installed-version contract before extending it.
- Treat `PreToolUse`, `PermissionRequest`, and `PostToolUse` as tool-path-specific. Current support covers Bash, `apply_patch` with `Edit`/`Write` matcher aliases, and MCP tool names when those paths expose hook payloads; it still does not cover `WebSearch` or every possible shell path.
- Treat `SubagentStart` and `SubagentStop` as agent-type-specific. `SubagentStop` with `decision: "block"` continues the subagent, not the parent turn.
- Treat `PreCompact` and `PostCompact` as compaction-trigger hooks. Their matcher values are `manual` and `auto`.
- Treat `Stop` carefully. For that event, `decision: "block"` means "continue Codex with this new prompt", not "reject the turn".

## Reading Guide

| Need | Read |
|------|------|
| Full audit checklist and planning questions | `references/project-analysis.md` |
| How to inspect and enable `hooks` safely | `references/feature-flag.md` |
| Current source-backed event list, matcher support, and output semantics | `references/hook-events.md` |
| Managed folder layout and plan file shape | `references/scaffold-layout.md` |
| Reusable script placement across Codex, Claude Code, OpenCode, Git hooks, and CI | `references/reusable-scripts.md` |
| Additive versus overhaul behavior | `references/merge-strategy.md` |
| Runtime limits, docs drift, and fail-open traps | `references/gotchas.md` |

## Operational Scripts

- `scripts/audit_project.sh` builds a project profile from real repo signals.
- `scripts/check_hooks_feature.py` inspects or enables `hooks` in user or project config.
- `scripts/scaffold_hooks.sh` renders the managed hook tree, manifest, fragment, README, and feature setup.
- `scripts/merge_hooks_json.sh` preserves non-managed handlers while replacing previously managed ones.
- `scripts/render_hooks_readme.sh` rebuilds `hooks/README.md` from the manifest and current plan.
- `scripts/validate.py` checks structure, frontmatter, manifest integrity, and cross-references.
- `scripts/test_skill.py` runs lightweight validation plus temp-project integration checks.

## Gotchas

1. The feature key is `hooks`; `codex_hooks` is only a legacy alias. Write the canonical key when editing config. Hooks are enabled by default today unless config or policy turns them off.
2. `matcher` is ignored for `UserPromptSubmit` and `Stop`. Do not design logic that depends on those matchers.
3. In the recorded baseline, `async`, `prompt`, and `agent` parse but are skipped with warnings. Later runtime support does not automatically extend the bundled generator.
4. Multiple matching command hooks for the same event run concurrently. One hook cannot stop another matching hook from starting.
5. `PostToolUse` cannot undo command side effects. At best it can replace the feedback Codex sees next.
6. `Stop` with `decision: "block"` continues Codex with a new prompt. It does not reject the turn.
7. `SubagentStop` with `decision: "block"` continues the subagent with a new prompt. Honor `stop_hook_active` to avoid loops.
8. Repo-local `.codex/config.toml` only loads in trusted projects. If you enable the feature in project scope but the project is not trusted, the effective feature can still look off.
9. Non-managed command hooks must be reviewed and trusted in `/hooks` before they run.
10. The bundled manifest lists ten hook events, including `SubagentStart` and `SubagentStop`. It is a historical baseline; resolve uncertain or changed event contracts against official release documentation before extending it.
11. Do not bury reusable validation or context logic inside harness-specific adapters. Put shared logic in `hooks/<event>/script.sh` or repo-owned scripts, and let `hooks/<event>/codex.sh` handle only Codex protocol adaptation.
