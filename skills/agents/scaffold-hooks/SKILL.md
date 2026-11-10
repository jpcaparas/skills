---
name: scaffold-hooks
description: "Audits, creates, migrates and refreshes agent lifecycle hooks for Claude Code, Codex, GitHub Copilot, Devin CLI and OpenCode, wired to repo-owned scripts. Use for /scaffold-hooks, hook setup, or hooks that never fire. Not for Git hooks or Husky."
---

# scaffold-hooks

Generates thin per-harness adapters that translate each harness's hook protocol and call project behaviour that lives in repo-owned scripts (for example `scripts/agent-stop-checks.sh <harness>`). Policy never belongs in the adapters.

**Emission rule:** an event gets files and a harness config entry only when the plan gives it at least one `scripts` or `commands` entry (OpenCode: a hook with at least one `actions` entry). Everything else is skipped, so a project never receives hooks that do nothing. A refresh removes the managed files and config entries of events that no longer qualify.

## Choosing harnesses

- The user names harnesses: pass exactly those with `--harnesses claude,codex,copilot,devin,opencode` (any subset).
- No harness named and the repo already has a hook surface (managed manifests, legacy generated roots, `hooks/` adapters, or harness config containing hooks): run without `--harnesses`. It refreshes only the detected set and never adds harnesses.
- Nothing detected: ask which harnesses; the default for a new scaffold is all five.
- Real hook behaviour is usually just session-start context and a stop check, so plan those first and add an event only when a repo script exists for it.

## Running it

```bash
scripts/scaffold_all_hooks.sh --project <dir> [--harnesses a,b] [--plan plan.json] [--mode additive|overhaul] [--dry-run]
```

Always `--dry-run` first (its `hooks to emit` line is the count of qualifying events), then run for real, then inspect `hooks/README.md`, `hooks/.state/scaffold-hooks/manifest.json`, the harness configs, and run the project's own validation. Start the plan from `templates/hook-plan.example.json`. Without `--plan`, a refresh reuses the plan recorded in `hooks/.state/scaffold-hooks/manifest.json`; a project never scaffolded gets nothing, and so does a plan whose events all lack behaviour. Read `references/plan-format.md` for plan fields, Stop code-change gating and output-path rules. Per-harness audit: `harnesses/<name>/scripts/audit_project.sh <dir>`.

Layout: for each qualifying event, `hooks/<event>/script.sh` runs the plan's scripts and commands, with one `<harness>.sh` and `<harness>.json` adapter pair beside it, `hooks/lib/` runtime, `hooks/.state/` manifests. Config stays where each harness reads it: `.claude/settings.json`, `.codex/hooks.json`, `.devin/hooks.v1.json`, `opencode.json` plus `.opencode/hook/hooks.md` (via `opencode-froggy`), and `.github/hooks/copilot-hooks.json` with generated events under `.github/copilot/hooks/generated/` (self-contained, because the Copilot cloud agent reads only committed files).

## Rules that are easy to get wrong

- Do not pass `overhaul` to a harness scaffolder directly. It would rewrite shared `script.sh` files. The universal script cleans selected adapters first, then calls harnesses additively.
- Migration from `.claude|.codex|.devin/hooks/generated`, or from an earlier scaffold that emitted a stub for every manifest event: strip those managed command entries, scaffold `hooks/`, delete legacy folders only if they contain a `manifest.json`, then grep final configs for the old roots. Read `references/migration.md`, and `references/collision-policy.md` before changing merge behaviour. Preserve custom hooks outside managed roots.
- Plans and existing hook config are executable policy, not data. Review commands and script paths before activating hooks or running tests that execute them. Output paths must be project-relative with no `..`, `~` or symlinks. OpenCode global scope and Codex user-scope feature activation need explicit user authorisation (`--allow-global-targets`); never change scope to get around a path check.
- OpenCode uses `opencode-froggy`. Do not recreate generated `.opencode/plugins/*.ts` adapters unless asked. Use Froggy's `isMainSession` condition on session hooks that should skip subagents.
- Hook stdout is protocol. JSON-output hooks print nothing on silent success and exactly one JSON payload otherwise; diagnostics go to stderr; predicates return status only (`grep -q`, never `| head -1`). Exit code carries success or block; stderr is not for success messages.
- Stop adapters default to `run_on_code_changes: true` with detected `code_change_extensions`, and must honour `stop_hook_active` to avoid loops.
- A shared `hookSpecificOutput.additionalContext` SessionStart shape is verified for Claude, Codex and Devin only; it says nothing about other events.
- Hooks that are registered but never fire: Claude Code needs workspace trust (`scripts/check_workspace_trust.sh <dir> --json` in `harnesses/claude/`; `--enable` edits `~/.claude.json` and needs the user's request). Codex needs the hooks feature (`harnesses/codex/scripts/check_hooks_feature.py`). Devin and Codex TUIs may show nothing even when hooks work; check `/hooks`, logs or transcripts.
- The bundled event manifests are snapshots (`harnesses/<name>/assets/hook-events.json`), last re-checked against the official docs on 2026-11-10. Verify an uncertain event contract against the installed version and official docs before relying on it. When a contract changed, update the manifest, its reference and the date with the source; when you cannot verify it, leave it and report it.
- OpenCode is unresolved: `opencode-froggy` 1.7.0+ no longer loads `.opencode/hook/hooks.md`, and OpenCode deprecates the `plugin` config key. Read `drift_2026_11_10` in `harnesses/opencode/assets/hook-events.json` before promising OpenCode hooks will run.

## Per-harness detail

Read only the file for the harness in play, when you need event semantics or hit a gotcha: `harnesses/<claude|codex|copilot|devin|opencode>/references/hook-events.md` and `gotchas.md`; also `harnesses/codex/references/feature-flag.md`, and for OpenCode `config-layering.md` and `plugin-patterns.md`.

Official docs: Claude `https://code.claude.com/docs/en/hooks`; Codex `https://developers.openai.com/codex/hooks`; Copilot `https://docs.github.com/en/copilot/reference/hooks-reference`; Devin `https://docs.devin.ai/cli/extensibility/hooks/overview`; OpenCode `https://opencode.ai/docs/plugins/` and `https://github.com/smartfrog/opencode-froggy`.
