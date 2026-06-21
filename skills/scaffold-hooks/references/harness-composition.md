# Harness Composition

`scaffold-hooks` is a composition skill. It does not own the hook event contracts for Claude Code, Codex, GitHub Copilot, Devin CLI, or OpenCode; each `harnesses/<name>/` component does.

## Delegation Order

Default order is:

1. Claude
2. Codex
3. Devin
4. OpenCode
5. Copilot

Claude runs first because it has the broadest lifecycle surface and its shared `script.sh` template is harness-neutral. Shell harness scaffolders skip existing `hooks/<event>/script.sh` files in additive mode, so later harnesses add adapters without rewriting shared behavior.

## Bare Refresh Selection

A universal run without `--harnesses` is conservative. With the default plan, the orchestrator detects existing supported hook surfaces and managed scaffold state before choosing harnesses:

- universal and per-harness managed manifests
- legacy generated manifests
- shared adapters under `hooks/`
- harness config files that already contain hook entries
- OpenCode Froggy config under `opencode.json` and `.opencode/hook/hooks.md`

If any harness is detected, only that detected set is refreshed. New harnesses are added only through explicit `--harnesses` or a custom universal plan.

## Why Shell Harnesses Run Additively

Universal `overhaul` mode means "refresh selected harness adapters and state," not "rewrite shared project behavior." The universal script performs targeted cleanup first:

- `hooks/.state/<harness>`
- `hooks/<event>/<harness>.sh`
- `hooks/<event>/<harness>.json`

Then it calls each shell harness scaffolder in additive mode so existing `script.sh` files stay stable.

## OpenCode

OpenCode remains different because the universal scaffold delegates the plugin layer to `opencode-froggy`. The component merges `opencode.json` so `plugin` includes `opencode-froggy`, then renders Froggy YAML frontmatter into `.opencode/hook/hooks.md`.

Froggy bash actions call repo-owned delegate scripts from the universal plan. Use Froggy's `isMainSession` condition on session lifecycle hooks that should skip child/subagent sessions.

The OpenCode managed manifest stores scaffold provenance, plan/template hashes, and managed file hashes under `.opencode/hook/.managed/`. Additive re-runs replace the managed Froggy block in `hooks.md`, preserve custom hooks outside that block, and remove prior scaffold-owned local plugin artifacts when `.opencode/plugins/.managed/manifest.json` proves ownership.

## Per-Harness Stdout Protocols for Shared Context Scripts

Shared scripts that emit session context (for example a repo-owned agent-session-context script) must branch on `AGENT_HOOK_HARNESS` because stdout contracts differ:

- `claude`: plain text or Claude JSON is accepted on `SessionStart`.
- `codex`: emit `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}`.
- `devin`: same `hookSpecificOutput` shape as codex. Devin strictly parses non-empty stdout as Claude-format JSON; plain text fails its effects evaluator and is silently dropped (only a `Failed to parse Claude hook output` warning in `~/.local/share/devin/cli/logs/`). Field-verified 2026-06-12 on v2026.5.26-8.

A safe default fall-through is plain text, but never let `devin` reach it.

## Exit Codes vs Output Streams

Keep the control plane separate from the text streams:

- Exit code `0` means success.
- Exit code `2` means "block" only for harnesses/events that define that behavior.
- Other nonzero exits mean failure or warning according to the harness.
- `stderr` is for diagnostics, failure detail, and block reasons. Do not write successful status or routine skip messages to stderr just to make them visible.
- Successful informational messages may go to stdout only when the harness stdout protocol allows free text. Otherwise keep successful no-op hooks quiet.

This matters for OpenCode Froggy because it displays stdout and stderr separately in its bash-result message. A successful skip on stderr looks like a warning even though the exit code is `0`.

## Hook Visibility Expectations

Codex CLI renders hook execution and context inline. Devin CLI runs hooks silently and renders nothing, even on success; verify via `/hooks`, the CLI logs, or the transcript JSON under `~/.local/share/devin/cli/transcripts/`. Mention this during scaffolding so users do not interpret silence as a broken scaffold.

## GitHub Copilot

Copilot stays self-contained like OpenCode. Its scaffolder enforces a managed root under `.github/copilot/hooks/generated/` and merges `.github/hooks/copilot-hooks.json`, because the Copilot cloud agent only reads hook configuration and scripts committed to the repository. The universal plan passes the Copilot nested plan through unchanged (no `managed_root` rewrite) and forwards `mode` directly. Shared project policy still lives in repo-owned scripts (for example `scripts/agent-stop-checks.sh copilot`) that Copilot's generated event scripts call.

## Updating Component Behavior

When an event name, matcher, output contract, or feature flag changes, update the harness component first:

- `harnesses/claude/`
- `harnesses/codex/`
- `harnesses/copilot/`
- `harnesses/devin/`
- `harnesses/opencode/`

Only update the universal orchestration after the harness component validates (`python3 harnesses/<name>/scripts/validate.py harnesses/<name>` and `python3 harnesses/<name>/scripts/test_skill.py harnesses/<name>`).
