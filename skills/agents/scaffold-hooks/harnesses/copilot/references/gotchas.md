# Gotchas

## `preToolUse` Fail-Closed

Symptom: a non-blocking logging hook unexpectedly denies a tool call.

Cause: GitHub documents command `preToolUse` hooks as fail-closed. A crash, timeout, or non-zero exit denies the tool call.

Fix: make observer `preToolUse` logic log errors to stderr and exit `0`. Use stdout JSON only when intentionally allowing, denying, asking, or modifying args.

## Exit Code `2` Is Not Devin's Blocking Model

Symptom: a generated Copilot `preToolUse` hook exits `2`, but behavior is not the intended hard deny.

Cause: Copilot uses event-specific exit-code semantics. Exit `2` is a `permissionRequest` deny shortcut and a `postToolUseFailure` context mechanism. For most events it is a warning, and for `preToolUse` explicit stdout JSON is the clearer denial path.

Fix: for `preToolUse`, write `{"permissionDecision":"deny","permissionDecisionReason":"..."}` to stdout and exit `0`.

## CLI-Only Events

Symptom: `permissionRequest` or `notification` does not run in cloud agent.

Cause: cloud agent is non-interactive with pre-approved tools and no user notification surface.

Fix: use `preToolUse` for cloud-compatible permission decisions. Keep `notification` for local Copilot CLI only.

## Hook Changes Not Loaded

Symptom: Copilot CLI keeps using the old hook configuration.

Cause: the official CLI docs say hook config changes are loaded when the CLI starts.

Fix: restart Copilot CLI after changing hook files.

## Matcher Patterns Are Anchored Regexes

Symptom: a matcher does not fire for expected tools.

Cause: matchers are full-value regexes anchored as `^(?:matcher)$`.

Fix: use `bash|edit|create` for multiple exact tool names, or a real regex. Do not use shell globs.

## Cloud Agent File Persistence

Symptom: hook logs disappear after a cloud agent job.

Cause: the cloud agent filesystem is ephemeral.

Fix: write durable results back to the repository, emit concise stderr logs, or use an allow-listed HTTP hook endpoint when retention is required.

## Cross-Tool Claude Settings

Symptom: Copilot CLI runs hooks that are not in `.github/hooks/*.json`.

Cause: GitHub documents that Copilot CLI can also read cross-tool `.claude/settings.json` and `.claude/settings.local.json` inline hooks.

Fix: inspect those files during audit, but keep generated Copilot hook scaffolds in `.github/hooks/*.json`.
