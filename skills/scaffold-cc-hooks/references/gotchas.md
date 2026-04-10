# Gotchas

## 1. Async does not mean smarter

The official docs now document `async: true`, but only for command hooks. Async hooks keep Claude moving, which is good for logging, notifications, and background tests. They cannot block or change the action they observed.

## 2. `if` is narrow and versioned

The official guide says `if` only works on tool events, and only in Claude Code v2.1.85 or later. If you put `if` on another event, the hook does not run.

## 3. `Stop` can loop forever

If a `Stop` hook asks Claude to continue, the next `Stop` hook invocation must check `stop_hook_active`. If you ignore that field, Claude can loop.

## 4. Hook shells are not your interactive shell

Hooks run in non-interactive shells. Aliases, shell prompts, and unconditional `echo` lines from `~/.bashrc` or `~/.zshrc` can break JSON output.

## 5. Use absolute project paths

The official docs recommend command paths rooted at `$CLAUDE_PROJECT_DIR`. Do not rely on relative paths or the current shell directory.

## 6. Headless mode skips `PermissionRequest`

The official guide says `PermissionRequest` does not fire in non-interactive `-p` mode. Use `PreToolUse` when you need a deterministic policy gate that also works there.

## 7. Multiple `updatedInput` writers fight each other

The official guide says multiple `PreToolUse` hooks that all rewrite input are non-deterministic because the last one to finish wins. Keep a single owner for input rewrites.

## 8. Do not silently delete non-managed hooks

The scaffold is only supposed to replace the managed generated layer. If the repo has custom hooks outside that layer, review them explicitly before removing anything.

