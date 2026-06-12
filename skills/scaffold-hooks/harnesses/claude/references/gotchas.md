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

The scaffold is only supposed to replace Claude adapters and `hooks/.state/claude`. If the repo has custom hooks or other harness adapters under `hooks/`, review them explicitly before removing anything.

## 9. Hooks silently do not fire in untrusted workspaces

Claude Code gates hook execution on a per-project trust flag stored in `~/.claude.json` under `.projects["/absolute/path/to/project"].hasTrustDialogAccepted`. Until that flag is `true`, hooks are registered and visible in `/hooks`, but they never execute. This is a deliberate security layer that prevents a cloned malicious repo from firing an arbitrary `PreToolUse` hook the moment it opens.

The failure mode is deceptive by design:

- `settings.json` parses cleanly and loads
- `/hooks` shows every registered hook with the right counts
- Hook scripts are executable and run fine standalone
- But nothing ever invokes them during a session, and there are no error messages

Treat this as the default first check when a user says hooks are not activating, not firing, or are being ignored. Also do it after a real scaffold if the next step is verifying that hooks work. The exact project path matters, so canonicalize it first with `pwd -P`.

Use the helper script for deterministic checks:

```bash
scripts/check_workspace_trust.sh /absolute/path/to/project --json
```

If the status comes back `untrusted`, tell the user exactly that and offer two recovery paths:

1. Start a new session from the project root. Claude Code prompts "Do you trust the files in this workspace?" - answer yes.
2. If the dialog does not re-prompt (already dismissed once), close all Claude Code sessions and flip the flag directly.

   Prefer the helper script when you are already using this skill:

   ```bash
   scripts/check_workspace_trust.sh /absolute/path/to/project --enable
   ```

   The direct `jq` equivalent is:

   ```bash
   jq '.projects["/absolute/path/to/project"].hasTrustDialogAccepted = true' \
     ~/.claude.json > ~/.claude.json.tmp && mv ~/.claude.json.tmp ~/.claude.json
   ```

Only mutate `~/.claude.json` when the user asks you to flip the flag or explicitly asks you to ensure trust is enabled. Otherwise, offer the check and explain the two recovery paths.

If hooks still do not fire in a fresh session, check `.projects[...]` in `~/.claude.json` before investigating settings, script permissions, or hook logic. It is almost always this flag.
