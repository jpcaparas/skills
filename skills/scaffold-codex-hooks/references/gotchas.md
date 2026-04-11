# Gotchas

## 1. Bash-only really means Bash-only

Current Codex `PreToolUse` and `PostToolUse` hooks only see Bash tool traffic. Valid regexes like `Edit|Write` still parse, but they do not match anything useful in the current runtime.

## 2. `matcher` is ignored for `UserPromptSubmit` and `Stop`

The current runtime strips matchers from those events. If your logic depends on a `Stop` matcher or a prompt matcher, the config shape may look correct while the behavior quietly stays broad.

## 3. `async`, `prompt`, and `agent` are config-shaped but not runtime-real

The current parser accepts those shapes, but the runtime skips them with warnings. Do not scaffold or recommend them as if they worked today.

## 4. Multiple matching hooks run concurrently

Matching command hooks from multiple files all run, and multiple matching handlers for the same event launch concurrently. One hook cannot stop another matching hook from starting. Avoid shared mutable state and ordering assumptions.

## 5. `PostToolUse` is reactive, not preventative

By the time `PostToolUse` runs, the Bash command already ran. You can replace the feedback Codex sees next, but you cannot undo the side effects.

## 6. `Stop` uses `block` to continue

For `Stop`, `decision: "block"` means "continue Codex with this new prompt text." It does not reject the turn in the normal policy sense.

## 7. Repo-local config needs an active project layer

The official config basics page says project config files only load when you trust the project. If `.codex/config.toml` contains `codex_hooks = true` but the effective feature stays off, the project layer may not be active yet.

## 8. Plain text stdout is not always safe

- `SessionStart` and `UserPromptSubmit` accept plain text stdout as extra developer context.
- `PreToolUse` and `PostToolUse` ignore plain text stdout.
- `Stop` requires JSON on stdout when exiting `0`.

Write the event-specific output contract into the generated stub comments and follow it.

## 9. Early articles drifted as the feature evolved

Some early writeups described fewer events or rougher semantics. Treat the official docs, generated schemas, and runtime source as the authority before you scaffold for real.
