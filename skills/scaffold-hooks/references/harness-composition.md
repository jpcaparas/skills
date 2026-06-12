# Harness Composition

`scaffold-hooks` is a composition skill. It does not own the hook event contracts for Claude Code, Codex, Devin CLI, or OpenCode.

## Delegation Order

Default order is:

1. Claude
2. Codex
3. Devin
4. OpenCode

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

## Per-Harness Stdout Protocols for Shared Context Scripts

Shared scripts that emit session context (for example a repo-owned agent-session-context script) must branch on `AGENT_HOOK_HARNESS` because stdout contracts differ:

- `claude`: plain text or Claude JSON is accepted on `SessionStart`.
- `codex`: emit `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "..."}}`.
- `devin`: same `hookSpecificOutput` shape as codex. Devin strictly parses non-empty stdout as Claude-format JSON; plain text fails its effects evaluator and is silently dropped (only a `Failed to parse Claude hook output` warning in `~/.local/share/devin/cli/logs/`). Field-verified 2026-06-12 on v2026.5.26-8.

A safe default fall-through is plain text, but never let `devin` reach it.

## Hook Visibility Expectations

Codex CLI renders hook execution and context inline. Devin CLI runs hooks silently and renders nothing, even on success; verify via `/hooks`, the CLI logs, or the transcript JSON under `~/.local/share/devin/cli/transcripts/`. Mention this during scaffolding so users do not interpret silence as a broken scaffold.

## Updating Component Behavior

When an event name, matcher, output contract, or feature flag changes, update the dedicated skill first:

- `{{ skill:scaffold-cc-hooks }}`
- `{{ skill:scaffold-codex-hooks }}`
- `{{ skill:scaffold-devin-hooks }}`
- `{{ skill:scaffold-opencode-hooks }}`

Only update this skill after the component skill validates.

