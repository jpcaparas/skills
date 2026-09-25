# Gotchas

Runtime details below describe the bundled `0.133.0` baseline, not every later release. See `PLAYBOOK.md` for known drift and the evidence-led update route.

## 1. The feature flag is `hooks`

Current Codex source and `codex features list` use canonical `[features].hooks`. The old `[features].codex_hooks` key is a legacy alias. When writing config, use `hooks = true`. Hooks are enabled by default today, so feature inspection is mainly for detecting explicit disables, legacy keys, or policy overrides.

## 2. Docs can lag runtime source

Docs and runtime source can describe different releases. On 2026-05-26, the baseline docs and schemas included ten events, adding `SubagentStart` and `SubagentStop` to an earlier eight-event set. Resolve uncertain or changing semantics with official release docs and source matching the installed CLI; `main` may include unreleased changes. No full source sweep is needed for a known local repair.

## 3. Tool hooks are broad, but not universal

`PreToolUse`, `PermissionRequest`, and `PostToolUse` can cover Bash, `apply_patch`, and MCP tool traffic when those paths expose hook payloads. They still do not cover `WebSearch`, every shell pathway, or arbitrary future tool implementations.

## 4. `apply_patch` uses aliases only for matching

File edits expose canonical `tool_name: "apply_patch"` to hook stdin. The matcher aliases `Edit` and `Write` can select the same hook, but hook scripts should key logs and policy on the canonical payload value.

## 5. `matcher` is ignored for `UserPromptSubmit` and `Stop`

The current runtime strips matchers from those events. If your logic depends on a `Stop` matcher or a prompt matcher, the config shape may look correct while the behavior quietly stays broad.

## 6. Parsed fields may lack effects in the bundled baseline

The baseline parser accepted `async`, `prompt`, and `agent`, but skipped them with warnings. Later official docs describe async command hooks; do not mistake either the historical runtime limit or the helper's current limitations for a perpetual platform rule. Extending the generator requires a separately verified contract change.

## 7. Multiple matching hooks run concurrently

Matching command hooks from multiple files all run, and multiple matching handlers for the same event launch concurrently. One hook cannot stop another matching hook from starting. Avoid shared mutable state and ordering assumptions.

## 8. `PostToolUse` is reactive, not preventative

By the time `PostToolUse` runs, the tool already ran. You can replace or add to the feedback Codex sees next, but you cannot undo side effects.

## 9. `PreCompact` and `PostCompact` do not use `decision:block`

Use `continue: false` and optional `stopReason` for compaction hooks. `decision: "block"` is invalid for compaction events.

## 10. `Stop` uses `block` to continue

For `Stop`, `decision: "block"` means "continue Codex with this new prompt text." It does not reject the turn in the normal policy sense.

## 11. `SubagentStop` also uses `block` to continue

For `SubagentStop`, `decision: "block"` means "continue the subagent with this new prompt text." Use `stop_hook_active` to avoid infinite continuation loops.

## 12. Repo-local config needs an active project layer

The official config basics page says project config files only load when you trust the project. If `.codex/config.toml` contains `hooks = true` but the effective feature stays off, the project layer may not be active yet.

## 13. Non-managed hook definitions need review

Codex requires review and trust for non-managed command hooks before they run. After scaffolding or changing `.codex/hooks.json`, open `/hooks` in Codex to review the hook definitions. If a project-local scaffold looks correct but does not run, check both project-layer trust and hook-definition trust before rewriting scripts.

## 14. Plain text stdout is not always safe

- `SessionStart`, `SubagentStart`, and `UserPromptSubmit` accept plain text stdout as extra developer context.
- `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, and `PostCompact` ignore plain text stdout.
- `SubagentStop` and `Stop` require JSON on stdout when exiting `0`.

Write the event-specific output contract into the generated stub comments and follow it.

## 15. There is no documented per-hook verbosity flag

The current official docs do not document a hook-specific `verbose` or `debug` switch.

For visibility, use the tools that are documented today:

- `statusMessage` for lightweight UI status text while a hook runs
- exit code `2` plus `stderr` when a hook needs to block, deny, or provide feedback
- `log_dir` in `config.toml` to control where Codex writes logs such as `codex-tui.log`
