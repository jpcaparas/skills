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

## Why Shell Harnesses Run Additively

Universal `overhaul` mode means "refresh selected harness adapters and state," not "rewrite shared project behavior." The universal script performs targeted cleanup first:

- `hooks/.state/<harness>`
- `hooks/<event>/<harness>.sh`
- `hooks/<event>/<harness>.json`

Then it calls each shell harness scaffolder in additive mode so existing `script.sh` files stay stable.

## OpenCode

OpenCode remains different because its extension point is a TypeScript or JavaScript plugin file. The universal scaffold keeps `.opencode/plugins/*.ts` as the OpenCode adapter layer and makes that plugin call:

- `hooks/opencode-session-created/opencode.sh`
- `hooks/opencode-session-idle/opencode.sh`

Those shell adapters then call repo-owned delegate scripts from the universal plan.

OpenCode also emits normal session lifecycle events for child/subagent sessions. The generated lifecycle plugin treats `session.created` with `info.parentID` as a child session marker, caches that session ID, and skips both context injection and idle validation for those child IDs so stop-style behavior remains main-thread only.

## Per-Harness Stdout Protocols for Shared Context Scripts

Shared scripts that emit session context (for example a repo-owned agent-session-context script) must branch on `AGENT_HOOK_HARNESS` because stdout contracts differ:

- `claude`: plain text or Claude JSON is accepted on `SessionStart`.
- `codex`: emit `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}`.
- `devin`: same `hookSpecificOutput` shape as codex. Devin strictly parses non-empty stdout as Claude-format JSON; plain text fails its effects evaluator and is silently dropped (only a `Failed to parse Claude hook output` warning in `~/.local/share/devin/cli/logs/`). Field-verified 2026-06-12 on v2026.5.26-8.

A safe default fall-through is plain text, but never let `devin` reach it.

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
